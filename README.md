# Docker simulation pipeline
This is an example project to demonstrate how one can easily scale simulation runs with docker containers.

## Introduction

### Docker
Docker is a great tool, which lets you orchestrate your software stack with scalable containers.
It is mainly used to deploy applications on a distributed cloud infrastructure.
An application once packed into a docker image is portable to every host running docker.
There are some issues when you move across architecture (e.g. x86 to ARM), but most of you will still work on x86 architectures.
For more information on docker please look out for some great tutorials at [docker.com](www.docker.com), [medium.com](www.medium.com) or [youtube.com](www.youtube.com) ...

### Docker for simulation tasks
In simulation you often want to run the same simulation with different parameter sets or configurations.
At a point in time, when the number of iterations and/or computation time grows, you might ask your self: "How can I scale up my simulation tasks".
Maybe you have access to a cloud computing infrastructure, maybe you have a big computing machine at your lab,
maybe you want to run your simulation on different hosts. Anyways, docker offers a great framework to scale up and orchestrate your simulation runs.

In this tutorial, I'm gonna show you how to set up und run a simulation pipeline using docker to parallelize your simulation tasks.

Note: In this tutorial I use 2 very simple examples to give you an idea of the main concept. Running those scripts in a docker container
may look a bit over engineered - and it is! Before you adapt this approach, ask your self: "How long is my main computation time  
compared to the time it takes to startup the docker container?"

## What you need
- Docker installed on your target machine (https://docs.docker.com/get-docker/)
- Python 3.7 (or newer) installed your target machine (https://www.python.org/downloads/)
- A GitHub user account (Needed to download docker images, from GitHubs container image registry)
- Git installed on your target machine (https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- (An IDE/Text Editor (VSCode, PyCharm, SublimeText)) - if you want to play around


## Basic concept
Our pipeline consists of three main parts:
1. A simulation, having a Dockerfile (e.g. `example_monte_carlo_pi`, `example_random_art`)
2. A GitHubActions pipeline, which test, builds and deploys your containerized simulation.
3. A Python script that orchestrates your simulation tasks in docker (`docker_sim_manager.py`)

<img src="img/concept.png" width="800" >

## Simulations
It doesn't matter what kind of simulation you are running. If it runs on your PC, you will be able to pack it into a docker image.
For sure it might get more complex than in the example projects, but you only have to deal with it once. Just make sure that your simulation
offers the possibility to parametrize it either via config-files or a cli.

For this tutorial I prepared two simple example simulations in Python: `example_monte_carlo_pi`, `example_random_art`

## Deploy your simulation in a docker image

### Create a Dockerfile
The blueprint of every docker image is a Dockerfile. It tells Docker how to build your image,
which software gets installed, which environment variables are set and which program should be ran at start.

Let's have a look at `example_random_art/Dockerfile`:

- It uses an existing image based on debian buster, along with python 3.9 preinstalled.
```docker
FROM python:3.9-buster
```
- TimeZone is set to `Europe/Berlin`
```docker
ENV TZ=Europe/Berlin
```

- The working directory is set to `/usr/src/app`
```docker
WORKDIR /usr/src/app`
```
- During build all files from the directory the Dockerfile lies in, get copied to the images working directory (in this case `usr/src/app`
```docker
COPY ./* ./
```

- The project dependencies get installed via `pip` and `poetry`
```docker
RUN pip install --upgrade pip
RUN pip install poetry
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi
```

- The images entrypoint is defined as
```docker
ENTRYPOINT ["python", "./sprithering.py"]
```

Out of this blueprint you are able to build a docker image locally on your machine running:

```shell script
docker build -t myimage:1.0
```

That's okay if you work on the same machine, where run your simulations, but gets annoying when you switch between different machines.  
Moreover, you would need to run `docker build` everytime you made changes on your source code. (Remember the simulation is packed into the container during its build. If you want apply changes you have to build a new version of your image)

### Test, Build and Deploy your Simulation with GitHub Actions
Modern CI/CD pipelines let you automate those tasks and fill in seemingly into your workflow. (Like the `Dockerfile` you just have to set it up once)
In this tutorial I will show you how to run such a pipeline with GitHub Actions (https://github.com/features/actions).  
The concept works also on other Platforms e.g. GitLab (https://docs.gitlab.com/ee/ci/). You will need to adapt the CI/CD pipeline to your requirements.

If you haven't heard about CI/CD at all so far, I would recommend you to look for some tutorials out there. Especially a proper CI/CD pipeline
with unit-tests can help you a lot with finding bugs in your code.

#### GitHubActions
GitHub Action jobs are collected in the directory `.github/` of your repository. GitHub will auto-check for those files on repository events.

Let' have a look at `.github/publish-monte-carlo-pi-docker`:


#### Configure action events
We define this script to run on every file change in `simulation_monte_carlo/**` after any push event.

```yaml
on:
  push:
    paths:
      - 'simulation_monte_carlo/**'
```

#### Specify jobs
The action script contains two jobs:
1. `test` Run unit tests and code-format checkers (This ensures, that you hopefully deploy a working version of your simulation)
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9]

    steps:
    - uses: actions/checkout@v2
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      working-directory: example_monte_carlo_pi
      run: |
        python -m pip install --upgrade pip
        pip install flake8
        pip install pytest
        pip install poetry
        poetry config virtualenvs.create false
        poetry install   
    - name: Lint with flake8
      run: |
        # stop the build if there are Python syntax errors or undefined names
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        # exit-zero treats all errors as warnings. The GitHub editor is 127 chars wide
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    - name: Test with pytest
      run: |
        pytest
```

2. `build_docker_and_push_to_registry` A Docker build and deploy task. This job runs only if the first one succeeds.
This job checks out the current version of the repository, and runs docker build and push with the given parameters.
   - `username`: Docker Registry Username. In this case: GitHub environment variable for the user triggering the action script
   - `password`: Docker Registry Password. In this case: Your Personal Access Token (PAT) with sufficient rights on your repository <ADD LINKS>
   - `dockerfile`: Path to your dockerfile inside the repository
   - `registry`: URL of your desired docker registry. In this case: GitHub Container Image Registry
   - `repository`: In this case: <YOUR_GITHUB_USERNAME>/<YOUR_REPOSITORY>/<DOCKER_IMAGE_NAME>
   - `tags`: Image tag. In this case: `latest`

For more infos have a look at (https://github.com/docker/build-push-action)
```yaml
build_docker_and_push_to_registry:
  needs: test
  runs-on: ubuntu-20.04
  steps:
    - name: Check out the repo
      uses: actions/checkout@v2
    - name: Set up QEMU
      uses: docker/setup-qemu-action@v1
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v1
    - name: Login to GitHub Container Registry
      uses: docker/login-action@v1
      with:
        registry: ghcr.io
        username: ${{ github.repository_owner }}
        password: ${{ secrets.CR_PAT }}
    - name: Build and push docker image
      uses: docker/build-push-action@v2
      with:
        context: ./example_monte_carlo_pi/
        file: example_monte_carlo_pi/Dockerfile
        platforms: linux/amd64,linux/arm64,linux/386
        push: true
        tags: ghcr.io/${{ github.repository_owner }}/docker_simulation_pipeline_example/monte-carlo-pi-image:latest
```

You can watch the results of your pipeline under `https://github.com/YOUR_NAMESPACE/YOUR_REPO/actions`:

<img src="img/actions_menu_bar.png" width="600">
<img src="img/workflows-overview.png" width="600">
<img src="img/workflow_details.png" width="600">

The images should now also be visible on your GitHub account (`https://github.com/<username>?tab=packages`):

<img src="img/packages.png">

<img src="img/packages_details.png">


### Pull your docker image
Let's verify that everything works properly, and let's pull the image to our local machine.

1. At the first time you must provide your login credentials for your container image registry
```shell script
docker login ghcr.io
```
2. Pull the image
```shell script
docker pull ghcr.io/michaelwittmann/docker_simulation_pipeline_example/monte-carlo-pi-image:latest
...
>e44af8ed0266: Pull complete
>Digest: sha256:77b65a3bb8deb5b4aa436d28a5dc7fc561b4882f2f115c3843b4afe1a7df23d4
>Status: Downloaded newer image for ghcr.io/michaelwittmann/docker_simulation_pipeline_example/monte-carlo-pi-image:latest
>ghcr.io/michaelwittmann/docker_simulation_pipeline_example/monte-carlo-pi-image:latest

```

3. Run the container
```shell script
docker run -it ghcr.io/michaelwittmann/docker_simulation_pipeline_example/monte-carlo-pi-image:latest
...
>Starting simulation: iterations=100000, random_seed=1
>Result: pi_hat = 3.1378400000
>Generation plot...
>Simulation finished! (0.12351 ms)

```

Alright your simulation gets now automatically deployed in a docker container and is ready to be used for parallel simulations!



## Orchestrate your simulations
That was a lot of work to setup the pipeline. Now its time to harvest the fruit of our efforts ;-).
We are now able to pull the latest version of our tested simulation, and are ready to run as many parallel versions of it as we want.

Therefore I wrote a small Python script which helps you to orchestrate your simulation jobs (`docker_sim_manager.py`) and two examples based on the previous container examples (`example_monte_carlo.py`, `example_random_art.py`)

### DockerSimManager
I wont go through the code line for line, but I'll give you a compact overview of the tasks/elements of the script:
- `DockerSimManager`: Main class, handling your docker containers.
  - `docker_container_url`: Simulation image URL at container image registry
  - `max_workers`: number of parallel workers
  - `data_directory`: path to the output directory on your host (This path gets mounted in your containers under `/mnt/data/`)
  - `docker_repo_tag`: container tag, Default: latest

- `SimJob`: A object, which represents a distinct simulation job. You can pass paths to template files, give it a name and specify the initial command appended on the containers entrypoint.
  - `sim_Name`: Simulation name (must be unique)
  - `templates`: files to be copied from your host to the container
  - `command`: command to be appended at containers entry point

- JobQueue: The `DockerSimManager` collects all your simulation tasks in a simple queue. Before run, you must submit `SimJobs` by adding them with `add_sim_job(<job>)`

- `start_computation()`: Starts computation of all jobs inside the queue. Jobs must be added before calling this function

- `_init_simulation()`: Prepares the simulation task

- `_authenticate_at_container_registry`: Authenticates at container registry. (If you choose other registries than gitHub, modify this function)


### Run your simulations
You can now run your simulation with 4 simple steps:
1. Specify an output folder on your host machine e.g.
```python
# Choose output directory on your host's file system
output_folder = Path.home().joinpath('example_docker_simulation')
```

2. Create a DockerSimManager object.
```python
 # Generate DockerSimManager object. Specify simulation image, number of parallel containers and output_path
docker_manager = DockerSimManager('ghcr.io/michaelwittmann/docker_simulation_pipeline_example/random-art-image',
                                  10,
                                  output_folder)
```

3. Add simulation jobs to the queue
```python
# Add 20 simulation jobs to the job queue
for i in range(1,10):
    docker_manager.add_sim_job(SimJob(f'randomArt_size{i}x{i}',None, command=f'-g {i} -i 30 -s 5000 -o /mnt/data -n 50'))

for i in range(1,10):
    docker_manager.add_sim_job(SimJob(f'random_Art_invaders_{i}',None, command=f'-g 10 -i {i} -s 5000 -o /mnt/data -n 50'))
```

4. Start computation
```python
# Start computation
docker_manager.start_computation()
```

### Run the examples

1. Install requirements
```
pip install poetry
poetry install
```

2. Run the example scripts
```
python example_monte_carlo_pi.py
```
AND/OR
```
python example_ramdom_art.py
```

3. Check the outputs

Windows
```
dir %systemdrive%%homepath%\example_docker_simulation
```

Linux
```
ls ~/example_docker_simulation
```


## Acknowledgements
Thanks to [Maximilian Speicher](https://github.com/maxispeicher) for the inspiration on this tutorial, and the first implementation of `DockerSimManager`

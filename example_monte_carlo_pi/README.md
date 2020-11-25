# Example | Monte Carlo Estimation of PI

If you draw random points on a square, $pi$ can be estimated by the ratio of points having a distance from the origin of less than 1  
and the total-sample-count, multiplied by 4.

This example project randomly samples points, estimats pi an generates a plot of your experiment.

## Basic Usage

### Install
1. This project uses poetry for dependency managment. First install poetry via pip
`pip install poetry`

2. Run poetry install in this directory
`poetry install`

### Run Script
This script provides a command line interface to specify the parameters of your experiment .
`python monte_carlo_pi.py - o <output_folder> -i <iterations> -r <random_seed>`

<ADD IMAGE HERE>

## Docker Container
The example is packed into a simple python docker container. The container is available in this repositories container registry.

### (Install Docker)
https://docs.docker.com/get-docker/

### Pull Docker container
`docker pull docker.pkg.github.com/michaelwittmann/docker_simulation_pipeline_example/monte-carlo-pi-image:latest`

### Run Docker container
```bash
docker run --name MonteCarloPi -it --mount type=bind,src=DIR_ON_YOUR_HOST,dst=/mnt/output/  docker.pkg.github.com/michaelwittmann/docker_simulation_pipeline_example/monte-carlo-pi-image:latest -o /mnt/output -i 100
```
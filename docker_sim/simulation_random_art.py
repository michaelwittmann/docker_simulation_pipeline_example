from docker_sim.docker_sim_manager import DockerSimManager
from pathlib import Path
from docker_sim.docker_sim_manager import SimJob
if __name__ == '__main__':

    sim_path = Path.home().joinpath('docker_sim')
    docker_manager = DockerSimManager('docker.pkg.github.com/michaelwittmann/docker_simulation_pipeline_example/random-art-image',
                                      1,
                                      sim_path)
    for i in range(1,10):
        docker_manager.add_sim_job(SimJob(f'size{i}x{i}',None, command=f'-g {i} -i 30 -s 5000 -o /mnt/data -n 50'))

    for i in range(1,10):
        docker_manager.add_sim_job(SimJob(f'invaders_{i}',None, command=f'-g 10 -i {i} -s 5000 -o /mnt/data -n 50'))

    docker_manager.start_computation()
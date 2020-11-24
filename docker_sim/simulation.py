from docker_sim.docker_sim_manager import DockerSimManager
from pathlib import Path
from docker_sim.docker_sim_manager import SimJob
if __name__ == '__main__':

    sim_path = Path.home().joinpath('docker_sim')
    docker_manager = DockerSimManager('docker.pkg.github.com/michaelwittmann/docker_simulation_pipeline_example/monte-carlo-pi-image',
                                      1,
                                      sim_path)
    for i in range(1,20):
        docker_manager.add_sim_job(SimJob(f'IT{i}',None, command=f'-o /mnt/data -r {i} -i 100'))
    docker_manager.start_computation()
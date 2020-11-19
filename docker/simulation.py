from docker.docker_sim_manager import DockerManager
from pathlib import Path

if __name__ == '__main__':

    sim_path = Path.home()
    docker_manager = DockerManager(4, 100,sim_path)
    docker_manager.start_computation()
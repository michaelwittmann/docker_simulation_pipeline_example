#!/usr/bin/env python
"""Example code to demonstrate DockerSimManager

This example generates random art in different scales and sizes
"""

from docker_sim_manager import DockerSimManager
from pathlib import Path
from docker_sim_manager import SimJob

__author__ = "Michael Wittmann"
__copyright__ = "Copyright 2020, Michael Wittmann"

__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Michael Wittmann"
__email__ = "michael.wittmann@tum.de"
__status__ = "Example"


if __name__ == '__main__':

    # Choose output  directory on your host's file system
    output_folder = Path.home().joinpath('example_docker_simulation').joinpath('random_art')

    # Generate DockerSimManager object. Specify simulation container, number of parallel containers and output_path
    docker_manager = DockerSimManager('docker.pkg.github.com/michaelwittmann/docker_simulation_pipeline_example/random-art-image',
                                      10,
                                      output_folder)

    # Add 20 simulation jobs to the job queue
    for i in range(1,10):
        docker_manager.add_sim_job(SimJob(f'randomArt_size{i}x{i}',None, command=f'-g {i} -i 30 -s 5000 -o /mnt/data -n 50'))

    for i in range(1,10):
        docker_manager.add_sim_job(SimJob(f'random_Art_invaders_{i}',None, command=f'-g 10 -i {i} -s 5000 -o /mnt/data -n 50'))

    # Start computation
    docker_manager.start_computation()
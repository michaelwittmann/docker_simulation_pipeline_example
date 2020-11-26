#!/usr/bin/env python
"""Example code to demonstrate DockerSimManager

This example runs multiple monte carlo simulations to estimate pi
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
    output_path = Path.home().joinpath('example_docker_simulation').joinpath('monte_carlo_pi')

    # Generate DockerSimManager object. Specify simulation container, number of parallel containers and output_path
    docker_manager = DockerSimManager('ghcr.io/michaelwittmann/docker_simulation_pipeline_example/monte-carlo-pi-image',
                                      1,
                                      output_path)

    # Add 20 simulation jobs to the job queue
    for i in range(1,20):
        docker_manager.add_sim_job(SimJob(f'IT{i}',None, command=f'-o /mnt/data -r {i} -i 100'))

    # Start computation
    docker_manager.start_computation()
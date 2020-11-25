#!/usr/bin/env python
"""Provides a light-weight framework to scale up simulations tasks with docker containers

Disclaimer: This code is part of an example project. In order to reduce complexity,
I decided to use a simple method and class design. There is still a massive potential in
error handling and generalization of methods and classes. Feel free to use this code as a
starting point.
"""

import datetime
import shutil
import threading
import time
from pathlib import Path
import concurrent.futures
import platform
import dateutil
import os
import docker
from docker.errors import DockerException, NotFound, APIError
from docker.types import Mount, LogConfig
from halo import Halo
from loguru import logger
from getpass import getpass

__author__ = "Michael Wittmann and Maximilian Speicher"
__copyright__ = "Copyright 2020, Michael Wittmann and Maximilian Speicher"

__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Michael Wittmann"
__email__ = "michael.wittmann@tum.de"
__status__ = "Example"


class SimJob():
    def __init__(self, sim_Name, templates:Path, command=None) -> None:
        """
        Creates a distinct job
        :param sim_Name: Simulation name (must be unique)
        :param templates: files to be copied from your host to the container
        :param command: command to be appended at containers entry point
        """
        self.templates = templates
        self.sim_Name = sim_Name
        self.command = command

class DockerSimManager():
    def __init__(self,
                 docker_container_url:str,
                 max_workers:int,
                 data_directory:Path,
                 docker_repo_tag= 'latest'
                 ) -> None:
        """

        :param docker_container_url: Simulation container URL at container registry
        :param max_workers: number of parallel workers
        :param data_directory: path to the output directory on your host
        :param docker_repo_tag: container tag, Default: latest
        """
        self._data_directory = data_directory
        self._max_workers = max_workers
        self._thread_pool_executor = concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers)
        self._container_prefix = 'DockerSim'
        self._docker_client = docker.from_env()
        self._authenticate_at_container_registry()
        with Halo(text='Pulling latest docker_sim image', spinner='dots'):
            self._docker_image = self._docker_client.images.pull(
                repository=docker_container_url,
                tag=docker_repo_tag
            )
        self._io_lock = threading.Lock()
        self._monitoring_frequency = 300
        self._minimum_runtime = 300
        self._maximum_inactivity_time = 30 * 60
        self.job_list = []


    def add_sim_job(self, job:SimJob)->None:
        """
        Adds a simulation job into the queue
        :param job: simulation job to be added
        """
        self.job_list.append(job)



    def start_computation(self):
        """
        Starts computation of all jobs inside the queue.
        Jobs must be added before calling this function
        """
        self.start_monitoring_thread()
        with self._thread_pool_executor as executor:
            futures = {executor.submit(self._process_sim_job, sim_job): sim_job
                       for sim_job in self.job_list}
            for future in concurrent.futures.as_completed(futures):
                logger.info(f'Thread for run {futures[future]} did finish')


    def _process_sim_job(self, sim_job: SimJob)->None:
        """
        Triggers processing steps for a single job.
        1. _init_simulation
        2. _run_docker_container
        3. _cleanup_sim_objects
        :param sim_job: SimJob to be processed
        :return: True if processing succeeded, False otherwise.
        """
        sim_paths = self._init_simulation(sim_job=sim_job)
        if sim_paths is None:
            logger.error(f'Error during initialization for simulation {sim_job.sim_Name}')
            return False

        try:
            (
                working_dir,
                *file_objects
            ) = sim_paths
        except:
            try:
                working_dir=sim_paths
            except:
                logger.error(f'Error during initialization for simulation {sim_job.sim_Name}')
                return False

        self._run_docker_container(container_name=sim_job.sim_Name, working_dir=working_dir, command=sim_job.command)
        self.cleanup_sim_objects(sim_job=sim_job, file_objects=file_objects)
        return True

    def _init_simulation(self, sim_job):
        """
        Initialize simulation. May be overridden with custom function.
        - Create output folders
        - Copy file templates
        - ...
        :param sim_job: SimJob to be processed
        :return: Path to working directory on your host's filesystem for this SimJob
        """
        # prepare your data for your scenario here
        output_folder_name = f'job_{sim_job.sim_Name}'
        working_dir = self._data_directory.joinpath(output_folder_name)
        try:
            with self._io_lock:
                working_dir.mkdir(exist_ok=False, parents=True)
                # if you need additional files in your simulation e.g. config files, data, add them here example_monte_carlo_pi here
            return working_dir
        except Exception as e:
            logger.warning(e)
            return None
        pass


    def _run_docker_container(self, container_name, working_dir, command):
        """
        Triggers the simulation run in a separate Docker container.
        :param container_name: the container's name
        :param working_dir: working directory on your host's file system
        :param command: container command (eg. name of script, cli arguments ...) Must match to your docker entry point.
        """
        try:
            system_platform = platform.system()
            if system_platform == "Windows":
                self._docker_client.containers.run(
                    image=self._docker_image,
                    command=command,
                    mounts=[Mount(
                        target='/mnt/data',
                        source=str(working_dir.resolve()),
                        type='bind'
                    )],
                    #working_dir='/simulation',
                    name=container_name,
                    environment={
                        # If you need add your environment variables here
                    },
                    log_config=LogConfig(type=LogConfig.types.JSON, config={
                        'max-size': '500m',
                        'max-file': '3'
                    })
                )
            else:
                user_id = os.getuid()
                self._docker_client.containers.run(
                    image=self._docker_image,
                    command=command,
                    mounts=[Mount(
                        target='/simulation',
                        source=str(working_dir.resolve()),
                        type='bind'
                    )],
                    working_dir='/simulation',
                    name=container_name,
                    environment={
                        # If you need add your environment variables here
                    },
                    log_config=LogConfig(type=LogConfig.types.JSON, config={
                        'max-size': '500m',
                        'max-file': '3'
                    }),
                    user=user_id
                )
        except DockerException as e:
            logger.warning(f'Could not run {container_name}: {e}.')
        finally:
            try:
                self.write_container_logs_and_remove_it(
                    container_name=container_name,
                    working_dir=working_dir
                )
            except NotFound:
                logger.warning(f'Can not save logs for {container_name}, because container does not exist')


    def start_monitoring_thread(self):
        """
        Start a monitoring thread, which observes running docker containers.
        """
        monitoring_thread = threading.Thread(target=self._monitor_containers,
                                             args=(self._container_prefix,),
                                             daemon=True,
                                             name='monitoring')
        monitoring_thread.start()

    def write_container_logs_and_remove_it(self, container_name, working_dir):
        """
        Write container logs and remove the container from your docker server
        :param container_name: The container's name, which shall be removed
        :param working_dir: path, where logfiles shall be written to
        """
        container = self._docker_client.containers.get(container_name)
        with open(working_dir.joinpath('log.txt'), 'w') as f:
            f.write(container.logs().decode('utf-8'))
        container.remove()

    def _authenticate_at_container_registry(self):
        """
        Authenticate at container registry. NOTE: GitHub container registry is used in this example.
        If you want to user other container registries, like DockerHub or GitLab, feel free to adapt this method.
        Function either uses Environment variables for authentication or asks for login credentials in the command line.
        Note: GitHub container registry does not accept your personal password. You need to generate a personal access token (PAT)
        """
        username = os.environ.get('GITHUB_USERNAME')
        password = os.environ.get('GITHUB_PAT')
        if username is None:
            username = input('Enter username for container registry: ')
        if password is None:
            password = getpass('Enter password for container registry: ')
        login_result = self._docker_client.login(
            registry='docker.pkg.github.com',
            username=username,
            password=password,
            reauth=True
        )
        if login_result['Status'] != 'Login Succeeded':
            raise RuntimeError("Could not authenticate at GitHub container registry")
        else:
            logger.info("Successfully authenticated at GitHub container registry.")

    def _monitor_containers(self, container_prefix):
        """
        Monitors all running docker containers. Inactive containers get killed after self._maximum_inactivity_time
        :param container_prefix: The containers prefix used for all containers in this simulation
        """
        while True:
            containers = self._docker_client.containers.list()
            for container in containers:
                try:
                    if container_prefix in container.name:
                        container_start = dateutil.parser.isoparse(container.attrs['State']['StartedAt'])
                        now = datetime.datetime.now(datetime.timezone.utc)
                        uptime = (now - container_start).total_seconds()

                        logs = container.logs(since=int(time.time() - self._maximum_inactivity_time))

                        if uptime > self._minimum_runtime and not logs:
                            logger.warning(f'Container {container.name} ran for more than '
                                           f'{self._minimum_runtime} seconds and showed no log activity for '
                                           f'{self._maximum_inactivity_time} seconds.'
                                           f'It will be stopped.')
                            container.stop()
                except APIError as e:
                    logger.warning(f'Error during thread monitoring: {str(e)}')

            time.sleep(self._monitoring_frequency)


    @staticmethod
    def cleanup_sim_objects(sim_job:SimJob, file_objects):
        """
        Clean up function for finished simulations. Removes all files given in file objects.
        :param sim_job: SimJob to be processed
        :param file_objects: files/directories to be removed after simulation
        """
        file_object:Path
        for file_object in file_objects:
            if file_object.is_file():
                try:
                    file_object.unlink()
                except Exception as e:
                    logger.warning(e)
                    logger.warning(f'Error during cleanup for simulation {sim_job.sim_Name}')
            elif file_object.is_dir():
                try:
                    shutil.rmtree(file_object)
                except Exception as e:
                    logger.warning(e)
                    logger.warning(f'Error during cleanup for simulation {sim_job.sim_Name}')
            else:
                logger.warning(f"{file_object} is not a file or directory.")
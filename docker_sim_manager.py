import datetime
import threading
import time
from pathlib import Path
import concurrent.futures
from sys import platform

import dateutil
import docker
from docker.errors import APIError, DockerException, NotFound
from docker.types import Mount, LogConfig
import os
from halo import Halo
from loguru import logger
from getpass import getpass

class DockerManager():

    def __init__(self, max_workers:int, number_of_simulations:int, data_directory: Path) -> None:
        self._data_directory = data_directory
        self._number_of_simulations = number_of_simulations
        self._max_workers = max_workers
        self._thread_pool_executor = concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers)
        self._container_prefix = 'PiMonteCarlo'
        self._docker_client = docker.from_env()
        self._authenticate_at_gitlab_registry()

        with Halo(text='Pulling latest docker image', spinner='dots'):
            #TODO: change image
            self._docker_image = self._docker_client.images.pull(
                repository='gitlab.lrz.de:5005/smartmobility/taxi/amod-taxi-munich',
                tag='latest'
            )

        self._io_lock = threading.Lock()

        self._monitoring_frequency = 300
        self._minimum_runtime = 300
        self._maximum_inactivity_time = 30 * 60


    def start_computation(self):
        self.start_monitoring_thread()

        with self._thread_pool_executor as executor:
            futures = {executor.submit(self._process_scenario, sim_run): sim_run
                       for sim_run in range(self._number_of_simulations)}
            for future in concurrent.futures.as_completed(futures):
                logger.info(f'Thread for run {futures[future]} did finish')

    def _run_simulation(self, sim_run: int):
        simulation_path = self._init_scenario(sim_run=sim_run)
        if simulation_path is None:
            logger.error(f'Error during initialization of simulation {sim_run}')
            return
        else:
            logger.debug(f'Starting container for simulation run {sim_run}')
            container_name = f'{self._container_prefix}_{sim_run}'
            command = 'INSERT YOUR COMMAND HERE'
            self._run_docker_container(container_name=container_name, working_dir=simulation_path, command=command)

    def _run_docker_container(self, container_name, working_dir, command):
        try:
            system_platform = platform.system()
            if system_platform == "Windows":
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
        except DockerException:
            logger.warning(f'Could not run {container_name}.')
        finally:
            try:
                self.write_container_logs_and_remove_it(
                    container_name=container_name,
                    working_dir=working_dir
                )
            except NotFound:
                logger.warning(f'Can not save logs for {container_name}, because container does not exist')

    def write_container_logs_and_remove_it(self, container_name, working_dir):
        container = self._docker_client.containers.get(container_name)
        with open(working_dir.joinpath('log.txt'), 'w') as f:
            f.write(container.logs().decode('utf-8'))
        container.remove()

    def _authenticate_at_gitlab_registry(self):
        username = os.environ.get('GITLAB_REGISTRY_USERNAME')
        password = os.environ.get('GITLAB_REGISTRY_PASSWORD')
        if username is None:
            username = input('Enter username for GitLab container registry: ')
        if password is None:
            password = getpass('Enter password for GitLab container registry: ')
        login_result = self._docker_client.login(
            registry='gitlab.lrz.de:5005',
            username=username,
            password=password,
            reauth=True
        )
        if login_result['Status'] != 'Login Succeeded':
            raise RuntimeError("Could not authenticate at GitLab container registry")
        else:
            logger.info("Successfully authenticated at GitLab container registry.")

    def _monitor_containers(self, container_prefix):
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

    def _init_scenario(self, sim_run):
        # prepare your data for your scenario here
        output_folder_name = f'it_{sim_run}'
        working_dir = self._data_directory.joinpath(output_folder_name)
        try:
            with self._io_lock:
                working_dir.mkdir(exist_ok=False, parents=True)
                # if you need additional files in your simulation e.g. config files, data, add them here simulation here
            return working_dir
        except Exception as e:
            logger.warning(e)
            return None


        pass
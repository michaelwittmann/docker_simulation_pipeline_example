import abc
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

class SimJob():
    def __init__(self, sim_Name, templates:Path, command=None) -> None:
        self.templates = templates
        self.sim_Name = sim_Name
        self.command = command

class DockerSimManager(abc.ABC):
    def __init__(self,
                 docker_container_url:str,
                 max_workers:int,
    #             number_of_simulations:int,
                 data_directory:Path, 

                 docker_repo_tag= 'latest'
                 ) -> None:
        
        self._data_directory = data_directory
    #    self._number_of_simulations = number_of_simulations
        self._max_workers = max_workers
        self._thread_pool_executor = concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers)
        self._container_prefix = 'DockerSim'
        self._docker_client = docker.from_env()
        self._authenticate_at_container_registry()
        with Halo(text='Pulling latest docker_sim image', spinner='dots'):
            #TODO: change image
            self._docker_image = self._docker_client.images.pull(
                repository=docker_container_url,
                tag=docker_repo_tag
            )
        self._io_lock = threading.Lock()
        self._monitoring_frequency = 300
        self._minimum_runtime = 300
        self._maximum_inactivity_time = 30 * 60
        self.job_list = []
        
        
    # @abc.abstractmethod
    # def _init_simulation(self, sim_name:str):
    #     pass
    #
    # @abc.abstractmethod
    # def _run_simulation(self, sim_name: str):
    #     pass
    
    def add_sim_job(self, job:SimJob):
        self.job_list.append(job)



    def start_computation(self):
        self.start_monitoring_thread()
        with self._thread_pool_executor as executor:
            futures = {executor.submit(self._process_sim_job, sim_job): sim_job
                       for sim_job in self.job_list}
            for future in concurrent.futures.as_completed(futures):
                logger.info(f'Thread for run {futures[future]} did finish')


    def _process_sim_job(self, sim_job: SimJob):
        sim_paths = self._init_simulation(sim_job=sim_job)
        if sim_paths is None:
            logger.error(f'Error during initialization for simulation {sim_job.sim_Name}')
            return

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
                return

        self._run_docker_container(container_name=sim_job.sim_Name, working_dir=working_dir, command=sim_job.command)
        self.cleanup_sim_objects(sim_job=sim_job, file_objects=file_objects)


    def _init_simulation(self, sim_job):
        # prepare your data for your scenario here
        output_folder_name = f'job_{sim_job.sim_Name}'
        working_dir = self._data_directory.joinpath(output_folder_name)
        try:
            with self._io_lock:
                working_dir.mkdir(exist_ok=False, parents=True)
                # if you need additional files in your simulation_monte_carlo_pi e.g. config files, data, add them here simulation_monte_carlo_pi here
            return working_dir
        except Exception as e:
            logger.warning(e)
            return None
        pass


    def _run_docker_container(self, container_name, working_dir, command):
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

    # def _run_simulation(self, sim_run: int):
    #     simulation_path = self._init_simulation(sim_run=sim_run)
    #     if simulation_path is None:
    #         logger.error(f'Error during initialization of simulation_monte_carlo_pi {sim_run}')
    #         return
    #     else:
    #         logger.debug(f'Starting container for simulation_monte_carlo_pi run {sim_run}')
    #         container_name = f'{self._container_prefix}_{sim_run}'
    #         command = 'INSERT YOUR COMMAND HERE'
    #         self._run_docker_container(container_name=container_name, working_dir=simulation_path, command=command)



    def start_monitoring_thread(self):
        monitoring_thread = threading.Thread(target=self._monitor_containers,
                                             args=(self._container_prefix,),
                                             daemon=True,
                                             name='monitoring')
        monitoring_thread.start()

    def write_container_logs_and_remove_it(self, container_name, working_dir):
        container = self._docker_client.containers.get(container_name)
        with open(working_dir.joinpath('log.txt'), 'w') as f:
            f.write(container.logs().decode('utf-8'))
        container.remove()

    def _authenticate_at_container_registry(self):
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
                logger.warning(f"{file_object=} is not a file or directory.")
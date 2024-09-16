from typing import Union, List, Dict, Iterable, TypeVar, Tuple

from docker.models.images import Image
from robot.api import logger
from docker.errors import APIError, ContainerError
from docker.models.containers import Container
import docker

from DockerLibrary.exceptions import DockerCreateConflictException, DockerContainerNotExistsException
from DockerLibrary.type import DockerContainerRunOptions, DockerContainerExecuteOptions

_T = TypeVar('_T', bytes, Iterable[bytes])


class DockerLauncher:
    _client = None

    def __new__(cls, *args, **kwargs):
        if not cls._client:
            cls._client = docker.from_env(**kwargs)

        return cls._client


class DockerContainerRunner:
    def __init__(self):
        self.image = None
        self.__options: Dict[str, Union[bool, str]] = {}
        self.container_name = None
        self.cur_container = None
        self.client = None

    def get_docker_client(self):
        self.client = DockerLauncher()
        return self.client

    def set_container_name(self, container_name: str):
        self.container_name = container_name

    def get_current_container_name(self) -> Union[str, None]:
        if isinstance(self.cur_container, Container):
            self.container_name = self.cur_container.name
            return self.container_name
        return None

    def get_options(self) -> Dict[str, Union[bool, str]]:
        return self.__options

    def is_detach(self) -> bool:
        return self.get_options().get(DockerContainerRunOptions.DETACH.value, False) is True

    def is_remove(self) -> bool:
        return self.get_options().get(DockerContainerRunOptions.REMOVE.value, False) is True

    def is_stream(self) -> bool:
        return self.get_options().get(DockerContainerExecuteOptions.STREAM.value) is True

    def get_image(self, repository, *args, **kwargs):
        self.image = self.client.images.pull(repository=repository, *args, **kwargs)

    def get_current_container(self, container_name: str = None) -> Union[None, Container]:
        # if self.cur_container is not None, use it
        if self.cur_container:
            logger.info(f"Container: '{self.cur_container.name}' found.")
            return self.cur_container

        # if self.cur_container is None but provide container_name and self.__option.get('detach')==True,
        # use container_name to find container and set self.cur_container
        # Firstly, you may use function self.run_image(...,name='test_target',detach=True) to create a container
        # Secondly, ou may use self.get_current_container(container_name='test_target')
        # Then, it will find container by container_name from all containers

        if container_name and self.is_detach():
            logger.info(f"Container: '{container_name}' found.")
            _cur_container = self.client.containers.get(container_name)
            if _cur_container:
                self.cur_container = _cur_container
            return self.cur_container

        warning_info = (
            f"Container: '{self.container_name}' not found."
            if self.container_name else "No container name provided."
        )
        logger.warn(warning_info)
        return None

    def set_options(self, used_new_config: bool = True, **kwargs):
        if used_new_config:
            self.__options = kwargs
        else:
            self.__options.update(kwargs)

    def refresh_options_from_params(self, params: Dict):
        self.set_options(**params)

    def run_image_by_entrypoint(
            self,
            entrypoint: Union[str, List],
            image: Union[str, Image] = None, command: Union[str, List] = None,
            volumes: list = None, environment: Union[List, Dict] = None,
            **kwargs
    ) -> Union[str, Container]:
        """

        :param entrypoint:
        :param image:
        :param command:
        :param volumes:
        :param environment:
        :return: if detach is True, return Container and return code
                 if detach is False, return str and return code
        """

        try:

            if kwargs:
                self.refresh_options_from_params(kwargs)

            container_result = self.client.containers.run(
                image=image if image is not None else self.image, name=self.container_name,
                entrypoint=entrypoint, command=command, volumes=volumes, environment=environment,
                **self.get_options()
            )
            if not self.is_detach():
                return self.parser_bytes(output=container_result)

            self.cur_container = container_result
            if self.container_name is None:
                self.get_current_container_name()

            return self.cur_container

        except APIError as api_error:
            if api_error.status_code == 409:
                raise DockerCreateConflictException(
                    message=api_error.explanation, status_code=api_error.status_code
                )
        except ContainerError as e:
            self.cur_container = e.container
            logs = self.run_container_logs(stream=True)
            return logs

        except Exception as e:
            raise e

    def run_image_by_bash_with_detach(
            self, image: Union[str, Image] = None,
            volumes: list = None, environment: Union[List, Dict] = None
    ) -> Container:
        """

        In this function, we will run a container with bash entrypoint and detach=True,stdin_open=True, tty=True.

        :param image:
        :param volumes:
        :param environment:
        :return:
        """
        try:
            _image = image if image is not None else self.image
            if _image is None:
                raise ValueError("Image is None.")

            self.cur_container = self.run_image_by_entrypoint(
                image=_image, entrypoint='bash', volumes=volumes,
                environment=environment,
                detach=True, stdin_open=True, tty=True
            )
            return self.cur_container
        except Exception as e:
            raise e

    def run_image_by_bash_and_return_exitcode_and_output(
            self,
            command: Union[str, List],
            image: Union[str, Image] = None,
            volumes: list = None,
            environment: Union[List, Dict] = None,
            container: Union[Container, None] = None,
            workdir: Union[None, str] = None
    ) -> Tuple[int, str]:
        """
        In container, we will run a command with bash entrypoint and return exit code(int) and output(string).

        :param command:
        :param image:
        :param volumes:
        :param environment:
        :param container:
        :param workdir:
        :return:
        """
        try:
            if container is None:
                container = self.run_image_by_bash_with_detach(image=image, volumes=volumes, environment=environment)
                logger.debug(f"Container: '{container.name}' created.")

            rc, output = self.run_container_exec(command=command, container=container, workdir=workdir)
            return rc, output

        except Exception as e:
            raise e

    def run_image(
            self, image: Union[str, Image] = None, command: Union[str, List] = None,
            volumes: list = None, environment: Union[List, Dict] = None
    ) -> Union[str, Container]:
        try:
            container_result = self.client.containers.run(
                image=image if image is not None else self.image,
                name=self.container_name,
                command=command, volumes=volumes, environment=environment,
                **self.get_options()
            )
            if not self.is_detach():
                return self.parser_bytes(output=container_result)

            self.cur_container = container_result
            if self.container_name is None:
                self.get_current_container_name()

            return self.cur_container

        except APIError as api_error:
            if api_error.status_code == 409:
                raise DockerCreateConflictException(
                    message=api_error.explanation, status_code=api_error.status_code
                )
            raise api_error
        except Exception as e:
            raise e

    def run_container_exec(
            self,
            *,
            command: Union[str, List],
            container: Union[Container, None] = None,
            workdir: Union[None, str] = None
    ) -> tuple[int, str]:
        _container = container if container else self.cur_container

        if _container is None:
            raise DockerContainerNotExistsException(container_name=self.container_name)

        rc, output = self.cur_container.exec_run(cmd=command, workdir=workdir, detach=False, stdin=True, tty=True)
        output = self.parser_bytes(output=output)

        return rc, output

    def run_container_logs(self, stream: bool = True) -> Union[str, None]:
        if self.cur_container:
            docker_logs = self.cur_container.logs(stream=stream)
            return self.parser_bytes(output=docker_logs)
        raise Exception("Current container is None.")

    def __docker_internal_init(self):
        self.__options = {}
        self.container_name = None
        self.cur_container = None

    def clean_container(self):
        # if you use client.containers.run to create a container with remove param,
        # it will not remove volume in this function
        # if self.container_name is None and self.cur_container is None:
        #     logger.debug(
        #         "Container name and current container are all None, "
        #         "No container information to support to clean."
        #     )
        #     return

        if self.is_remove():
            logger.debug("Remove volumes and init params about docker.")
            self.client.volumes.prune()
            self.__docker_internal_init()
            return

        container = self.cur_container if self.cur_container else self.client.containers.get(self.container_name)
        if container:
            container.stop()
            container.remove(force=True, v=True)
        else:
            logger.warn(f"Container: '{self.container_name}' not found.")

        self.__docker_internal_init()
        return

    @staticmethod
    def parser_bytes(output: _T) -> str:
        if isinstance(output, bytes):
            return output.decode('utf-8')

        _output = ''
        for chunk in output:
            _output += chunk.decode('utf-8')
        return _output

    def init_docker_test_environment(self, container_name: str, repository: str, tag: str):
        logger.info(
            f"Init docker test environment with container name: {container_name},"
            f" test image: {repository}:{tag}"
        )
        self.get_docker_client()
        self.set_container_name(container_name=container_name)
        self.get_image(repository=repository, tag=tag)

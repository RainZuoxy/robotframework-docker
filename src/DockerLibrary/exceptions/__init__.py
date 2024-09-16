from docker.errors import DockerException


class DockerCreateConflictException(DockerException):
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code

    def __str__(self):
        return self.message


class DockerContainerNotExistsException(DockerException):
    def __init__(self, *, container_name: str = None, container_id: str = None):
        self.container_name = container_name
        self.container_id = container_id

    def __str__(self):
        match self.container_name, self.container_id:
            case None, None:
                return "Docker Container Object has not been assigned."
            case self.container_name, None:
                return f"Docker Container '{self.container_name}' does not exist."
            case None, self.container_id:
                return f"Docker Container with ID '{self.container_id}' does not exist."
            case self.container_name, self.container_id:
                return f"Docker Container '{self.container_name}' with ID '{self.container_id}' does not exist."

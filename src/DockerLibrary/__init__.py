from DockerLibrary.keywords import DockerContainerRunner


class DockerLibrary(DockerContainerRunner):
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = __version__

    def __init__(self):
        super().__init__()
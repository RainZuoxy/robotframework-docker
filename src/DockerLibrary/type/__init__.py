from dataclasses import dataclass
from enum import Enum


@dataclass
class DockerContainerRunOptions(str, Enum):
    DETACH = 'detach'
    TTY = 'tty'
    INTERACTIVE = 'stdin_open'
    REMOVE = 'remove'


@dataclass
class DockerContainerExecuteOptions(str, Enum):
    DETACH = 'detach'
    TTY = 'tty'
    INTERACTIVE = 'stdin'
    STREAM = 'stream'

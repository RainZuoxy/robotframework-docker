from setuptools import setup, find_packages


def get_reqs(req_file):
    with open(req_file) as f:
        return [line for line in f]


DESCRIPTION = "Robot Framework test library for docker"
setup(
    name="robotframework-docker",
    version="0.0.1",
    normalized_version=False,
    description='Robot Framework test library for docker',
    long_description=DESCRIPTION,
    install_requires=get_reqs("requirements.txt"),
    package_dir={'': 'src'},
    packages=find_packages(where="src"),
    setup_requires=["pytest-runner", ],
    include_package_data=True
)

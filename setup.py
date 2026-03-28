import os 
from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install


cwd = os.path.dirname(os.path.abspath(__file__))
version_file = os.path.join(cwd, 'VERSION')

with open(version_file, encoding='utf-8') as f:
    package_version = f.read().strip()

with open('requirements.txt') as f:
    reqs = f.read().splitlines()
class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install.run(self)
        os.system('python -m unidic download')


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        develop.run(self)
        os.system('python -m unidic download')

setup(
    name='melotts',
    version=package_version,
    python_requires='>=3.10',
    packages=find_packages(),
    include_package_data=True,
    install_requires=reqs,
    package_data={
        '': ['*.txt', 'cmudict_*'],
    },
    entry_points={
        "console_scripts": [
            "melotts = melo.main:main",
            "melo = melo.main:main",
            "melo-ui = melo.app:main",
        ],
    },
)

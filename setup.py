import os 
from setuptools import setup, find_packages


cwd = os.path.dirname(os.path.abspath(__file__))
version_file = os.path.join(cwd, 'VERSION')

with open(version_file, encoding='utf-8') as f:
    display_version = f.read().strip()

package_version = display_version.removeprefix('v').replace('-SNAPSHOT', '.dev0')

with open('requirements.txt') as f:
    reqs = f.read().splitlines()

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

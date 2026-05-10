import os 
from setuptools import setup, find_packages


cwd = os.path.dirname(os.path.abspath(__file__))
version_file = os.path.join(cwd, 'VERSION')

with open(version_file, encoding='utf-8') as f:
    package_version = f.read().strip()

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
        'melo': ['web/*.html', 'web/*.css', 'web/*.js'],
    },
    entry_points={
        "console_scripts": [
            "melotts = melo.main:main",
            "melo = melo.main:main",
            "melo-ui = melo.app:main",
        ],
    },
)

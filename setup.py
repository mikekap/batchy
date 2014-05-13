import os
import itertools
import versioneer
from setuptools import setup, find_packages
from distutils.command.sdist import sdist

versioneer.VCS = 'git'
versioneer.versionfile_source = 'batchy/_version.py'
versioneer.versionfile_build = 'batchy/_version.py'
versioneer.tag_prefix = ''
versioneer.parentdir_prefix = 'batchy-'

setup(
    name='batchy',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='vine batching framework',
    author='vine',
    author_email='mikekap@vine.co',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=[
        'blinker>=1.2',
    ],
    setup_requires=['nose>=1.0'],
)


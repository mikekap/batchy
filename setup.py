import versioneer
from setuptools import setup, find_packages

versioneer.VCS = 'git'
versioneer.versionfile_source = 'batchy/_version.py'
versioneer.versionfile_build = 'batchy/_version.py'
versioneer.tag_prefix = ''
versioneer.parentdir_prefix = 'batchy-'

setup(
    name='batchy',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='batching framework',
    long_description='https://github.com/mikekap/batchy',
    url='https://github.com/mikekap/batchy',
    author='Mike Kaplinskiy',
    author_email='mike.kaplinskiy@gmail.com',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=[
        'blinker>=1.2',
    ],
)

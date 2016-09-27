#!/usr/bin/env python

import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='DockerPy-Helpers',
    version='0.1',
    description='Support Tools for the Docker-based environments',
    long_description=read('README.rst'),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Environment :: Console',
        'Programming Language :: Python :: 3.4',
        'Topic :: Utilities',
        'License :: Other/Proprietary License'
    ],
    keywords='docker daemon dns',
    author='Dennis Twardowsky',
    author_email='twardowsky@gmail.com',
    license='proprietary',
    packages=[
        'extdocker',
        'extdocker/helpers',
    ],
    scripts=[
        'bin/dockerdns.py',
        'bin/dockerRmUnknown.py'
    ],
    data_files=[
        ('/lib/nagios/plugins', ['lib/nagios/plugins/check_docker.py'])
    ],
    install_requires=[
        'docker-py',
        'nagiosplugin',
        'pyyaml'
    ],
    include_package_data=True,
    zip_safe=False
)

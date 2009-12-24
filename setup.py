"""Installs CherryPy using distutils

Run:
    python setup.py install

to install this package
"""

from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES
import sys
import os
import shutil
import pyndk

required_python_version = '2.6+'
setup(
    name             = 'pyndk',
    version          = pyndk.version,
    description      = "Python Object-Oriented Network Develop Framework",
    long_description = "An implementation of 'Reactor Mode' in python, object-oriented network develop framework",
    author           = 'Cui Shaowei',
    author_email     = 'shaovie@gmail.com',
    platforms        = 'linux',
    license          = 'GPLv3',
    package_dir      = {'pyndk': 'pyndk'},
    packages         = ['pyndk'],
    )

#!/usr/bin/env python

"""Setup script for the 'pybaidudisk' distribution."""

setup_args = {
    'name' : 'pybaidudisk',
    'version' : '0.1',
    'url': 'https://github.com/lovesnow/pybaidudisk',
    'description' : 'baidu netpan for python binding library',    
    'author': 'andelf',
    'maintainer': 'evilbeast',
    'maintainer_email': 'houshao55@gmail.com',
    'packages': ['pybaidudisk'],
    'scripts' : ['scripts/bdiskcmd'],
    }

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
else:
    setup_args['install_requires'] = ['pycurl']

setup(**setup_args)

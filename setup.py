# -*- coding: utf-8 -*-

import re
import ast
from setuptools import setup

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('ipybind/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
    name='ipybind',
    author='Ivan Smirnov',
    author_email='i.s.smirnov@gmail.com',
    license='MIT',
    version=version,
    url='http://github.com/aldanor/ipybind',
    packages=['ipybind'],
    description='IPython and Jupyter integration for pybind11.',
    install_requires=['ipython', 'pybind11'],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3'
    ]
)

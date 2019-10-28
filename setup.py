#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='grobid-client-python',
      version='0.0.1',
      description='grobid-client-python',
      author='kermitt2',
      packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
      license='LICENSE',
    )

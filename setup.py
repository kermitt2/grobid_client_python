#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='pygrobid',
      version='0.0.2',
      description='A python client for Grobid service',
      author='Samuel.Wu',
      packages=find_packages(exclude=["*.tests", "*.tests.*",
                                      "tests.*", "tests"]),
      license='LICENSE')

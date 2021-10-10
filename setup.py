#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='grobid_client_python',
      version='0.0.2',
      description='grobid_client_python',
      author='kermitt2',
      packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
      install_requires=['requests'],
      entry_points={
          'console_scripts': ['grobid_client=grobid_client.grobid_client:main']
      },
      license='LICENSE',
    )

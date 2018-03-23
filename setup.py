#!/usr/bin/env python3

from setuptools import find_packages, setup

with open('LICENSE') as f:
    LICENSE = f.read()

setup(
   name='ccoin',
   version='0.0.1dev',
   author='Rustem Kamun <xepa4ep>',
   author_email='r.kamun@gmail.com',
   description='Toy implementation of blockchain with Proof-of-Authority(PoA).',
   license=LICENSE,
   packages=find_packages(),
)
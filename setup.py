# -*- coding: utf-8 -*-

# Learn more: https://git.digilab.ocpgroup.ma/m.akkouh/mine2farm/setup.py

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='sample',
    version='0.1.0',
    description='Mine2Farm, modeling the supply-chain',
    long_description=readme,
    author='OCP Solutions',
    author_email='mahdi.akkouh@ocpsolutions.ma',
    url='https://git.digilab.ocpgroup.ma/m.akkouh/mine2farm',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'), install_requires=['pandas'])
)

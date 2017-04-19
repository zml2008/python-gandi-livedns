#!/usr/bin/env python

import os
from setuptools import setup, find_packages

# From https://pythonhosted.org/an_example_pypi_project/setuptools.html
# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name="gandi-livedns",
        use_scm_version=True,
        author="Zach Levis",
        author_email="zml+gandilivedns@aoeu.xyz",
        license="Apache v2",
        keywords="gandi dns livedns api",
        long_description=read("README.md"),
        packages=find_packages("src"),
        package_dir={'': 'src'},
        install_requires=[
            "click>=6",
            "requests",
            ],
        setup_requires=[
            "setuptools_scm"
            ],
        entry_points={
            "console_scripts": [
                "gandi-livedns = livedns.cli:main"
                ]
            }
        )

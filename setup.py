# -*- coding: utf-8 -*-
from setuptools import setup
from codecs import open
from os import path

here = path.realpath(path.dirname(__file__))

with open(path.join(here, "README.rst"), encoding="utf-8") as fp:
    long_description = fp.read()

setup(
    name="i8c",
    version="0.0.1",
    description="Infinity note compiler",
    long_description=long_description,
    license="GPLv3+",
    author="Gary Benson",
    author_email="gbenson@redhat.com",
    url="https://github.com/gbenson/i8c/",
    classifiers=[
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved" +
            " :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Compilers",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
    ],
    packages=["i8c", "i8c.compiler", "i8c.runtime"],
    entry_points={"console_scripts": ["i8c = i8c.compiler:main",
                                      "i8x = i8c.runtime:main"]},
    tests_require=["nose"],
    test_suite="nose.collector")

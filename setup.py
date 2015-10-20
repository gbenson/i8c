# -*- coding: utf-8 -*-
# Copyright (C) 2015 Red Hat, Inc.
# This file is part of the Infinity Note Compiler.
#
# The Infinity Note Compiler is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# The Infinity Note Compiler is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Infinity Note Compiler.  If not, see
# <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# Python2 distutils can't cope with __future__.unicode_literals

from setuptools import find_packages, setup
from codecs import open
from os import path

here = path.realpath(path.dirname(__file__))

with open(path.join(here, "README.rst"), encoding="utf-8") as fp:
    long_description = fp.read()

setup(
    name="i8c",
    version="0.0.1",
    description="Infinity Note Compiler",
    long_description=long_description,
    license="GPLv3+ and LGPLv2.1+",
    author="Gary Benson",
    author_email="infinity@sourceware.org",
    url="https://sourceware.org/gdb/wiki/Infinity",
    classifiers=[
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved" +
            " :: GNU General Public License v3 or later (GPLv3+)",
        "License :: OSI Approved" +
            " :: GNU Lesser General Public License v2 or later (LGPLv2+)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Compilers",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ],
    packages=find_packages("src"),
    package_dir = {"": "src"},
    entry_points={"console_scripts": ["i8c = i8c.compiler:main",
                                      "i8x = i8c.runtime:main"]},
    tests_require=["nose"],
    test_suite="nose.collector")

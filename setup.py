# -*- coding: utf-8 -*-
# Copyright (C) 2015-16 Red Hat, Inc.
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
import sys

here = path.realpath(path.dirname(__file__))

with open(path.join(here, "README.rst"), encoding="utf-8") as fp:
    long_description = fp.read()

# Remember to update requirements.txt
install_requires = [
    "arpy",
    "pyelftools >= 0.24",
]

# Ensure we have a suitable unittest
try:
    import unittest2 as unittest
except ImportError:
    import unittest
if not hasattr(unittest.TestCase, "assertIsInstance"):
    install_requires.append("unittest2")

# Ensure we don't ever release packages requiring unittest2
if "unittest2" in install_requires:
    for arg in sys.argv[1:]:
        for bail in ("register", "upload", "dist"):
            if arg.find(bail) >= 0:
                print("Don't use Python %s.%s for ‘%s’"
                      % (sys.version_info[:2] + (arg,)))
                sys.exit(1)

setup(
    name="i8c",
    version="0.0.4",
    description="Infinity Note Compiler",
    long_description=long_description,
    license="GPLv3+ and LGPLv2.1+",
    author="Gary Benson",
    author_email="infinity@sourceware.org",
    url="https://infinitynotes.org/",
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
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ],
    packages=find_packages("src"),
    package_dir = {"": "src"},
    install_requires=install_requires,
    entry_points={"console_scripts": ["i8c = i8c.compiler:main",
                                      "i8x = i8c.runtime:main"]},
    tests_require=["nose"],
    test_suite="nose.collector")

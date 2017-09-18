# -*- coding: utf-8 -*-
# Copyright (C) 2016-17 Red Hat, Inc.
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
from __future__ import unicode_literals

from .. import constants
import copy
import os
import struct
import subprocess
import tempfile

class CompilerCommand(object):
    def __init__(self, args=None):
        if args is None:
            args = self.DEFAULT
        self.args = copy.copy(args)

    def check_call(self, *args, **kwargs):
        return self.__call(subprocess.check_call, *args, **kwargs)

    def Popen(self, *args, **kwargs):
        return self.__call(subprocess.Popen, *args, **kwargs)

    def __call(self, func, extra_args=(), **kwargs):
        return func(self.args + list(extra_args), **kwargs)

def _getenv(name, default):
    result = os.environ.get(name, None)
    if result is not None:
        return result.split()
    else:
        return copy.copy(default)

# Program for compiling C programs.
_I8C_CC = _getenv("I8C_CC", ["gcc"])

class Preprocessor(CompilerCommand):
    """Program for running the C preprocessor, with results
    to standard output.
    """
    DEFAULT = _getenv("I8C_CPP",
                      _I8C_CC + ["-E",
                                 "-x", "assembler-with-cpp",
                                 "-D__INFINITY__"])

class Assembler(CompilerCommand):
    """Program for compiling assembly language files.
    """
    DEFAULT = _getenv("I8C_AS", _I8C_CC)

    def __init__(self, *args, **kwargs):
        super(Assembler, self).__init__(*args, **kwargs)
        self.__last_probed = ()

    @property
    def output_wordsize(self):
        self.__maybe_probe_output()
        return self.__wordsize

    def __maybe_probe_output(self):
        current_args = tuple(self.args)
        if current_args == self.__last_probed:
            return

        hdrfmt = b"4sB"
        hdrlen = struct.calcsize(hdrfmt)
        with tempfile.NamedTemporaryFile(suffix=".o") as of:
            with tempfile.NamedTemporaryFile(suffix=".S") as cf:
                self.check_call(("-c", cf.name, "-o", of.name))
                with open(of.name, "rb") as fp:
                    header = fp.read(hdrlen)

        magic, elfclass = struct.unpack(hdrfmt, header)
        assert magic == constants.ELFMAG

        self.__wordsize = {constants.ELFCLASS32: 32,
                           constants.ELFCLASS64: 64}[elfclass]

        self.__last_probed = current_args

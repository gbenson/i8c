# -*- coding: utf-8 -*-
# Copyright (C) 2016 Red Hat, Inc.
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

from . import commands
from . import I8CError
from . import warn
import copy
import struct
import subprocess
import tempfile

class TargetAnnotator(object):
    def __init__(self, commandline):
        self.args = commandline

    def visit_toplevel(self, toplevel):
        # Look for "wordsize" directives in the source.
        self.wordsize = None
        for node in toplevel.wordsize_directives:
            node.accept(self)
        toplevel.wordsize = self.wordsize

        # If no wordsize was specified in the source but we
        # have enough information to run the compiler then
        # we compile an empty file and look at the output.
        if (toplevel.wordsize is None and self.args is not None):
            asmargs = self.__process_sco_args(self.args.asm_args)
            toplevel.wordsize = guess_wordsize(asmargs)
            if toplevel.wordsize is not None:
                if not self.args.with_asm:
                    warn("assuming ‘wordsize %d’" % toplevel.wordsize)

        # If nothing worked we can't continue.
        if toplevel.wordsize is None:
            raise I8CError("unable to determine target wordsize")

    def visit_wordsize(self, wordsize):
        for node in wordsize.children:
            node.accept(self)

    def visit_constant(self, constant):
        assert self.wordsize is None
        self.wordsize = constant.value

    def __process_sco_args(self, src):
        src = copy.copy(src)
        dst = []
        while src:
            arg = src.pop(0)
            if arg == "-o":
                src.pop(0)
            elif arg == "-c" or arg.startswith("-o"):
                continue
            else:
                dst.append(arg)
        return dst

def guess_wordsize(args=None):
    if args is None:
        args = []

    hdrfmt = b"4sB"
    hdrlen = struct.calcsize(hdrfmt)
    try:
        with tempfile.NamedTemporaryFile(suffix=".o") as of:
            with tempfile.NamedTemporaryFile(suffix=".c") as cf:
                command = (commands.I8C_CC
                           + args
                           + ["-c", cf.name, "-o", of.name])
                subprocess.check_call(command)
                with open(of.name, "rb") as fp:
                    header = fp.read(hdrlen)
    except:
        return

    magic, elfclass = struct.unpack(hdrfmt, header)
    if magic == b"\x7fELF":
        return {1: 32, 2: 64}.get(elfclass, None)

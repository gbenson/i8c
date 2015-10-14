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

from i8c import compiler
from i8c import runtime
from i8c.runtime.testcase import BaseTestCase
import os
import StringIO as stringio
import struct
import subprocess

class SourceReader(stringio.StringIO):
    def readline(self):
        line = stringio.StringIO.readline(self)
        trim = line.find("//")
        if trim >= 0:
            line = line[:trim] + "\n"
        return line

class TestOutput(runtime.Context):
    def __init__(self, testcase, index, asm):
        runtime.Context.__init__(self)
        self.__set_fileprefix(testcase, index)
        # Store the assembly language we generated
        asmfile = self.fileprefix + ".S"
        open(asmfile, "w").write(asm)
        # Assemble it
        objfile = self.fileprefix + ".o"
        subprocess.check_call(["gcc", "-c", asmfile, "-o", objfile])
        # Load the notes from it
        self.import_notes(objfile)
        self.notes = []
        for notes in self.functions.values():
            self.notes.extend(notes)
        # Make sure we got at least one note
        testcase.assertGreaterEqual(len(self.notes), 1)
        # Setup for note execution
        self.env = testcase

    def __set_fileprefix(self, testcase, index):
        test_id = testcase.id().split(".")
        # Remove the common prefix
        for expect in "i8c", "tests":
            actual = test_id.pop(0)
            assert actual == expect
        # Remove the name of the class
        test_id.pop(-2)
        # Build the result
        index = "_%04d" % index
        self.fileprefix = os.path.join(
            testcase.topdir, "tests.out", *test_id) + index
        # Ensure the directory we'll write to exists
        dir = os.path.dirname(self.fileprefix)
        if not os.path.exists(dir):
            os.makedirs(dir)

    @property
    def note(self):
        assert len(self.notes) == 1
        return self.notes[0]

    @property
    def ops(self):
        ops = self.note.ops.items()
        ops.sort()
        return [op for pc, op in ops]

    @property
    def opnames(self):
        return [op.name for op in self.ops]

class TestCase(BaseTestCase):
    def __locate_topdir(self):
        self.topdir = os.path.realpath(__file__)
        self.topdir, check = os.path.split(self.topdir)
        assert check.startswith("__init__.py")
        for expect in ("tests", "i8c"):
            self.topdir, check = os.path.split(self.topdir)
            assert check == expect
        assert os.path.exists(os.path.join(self.topdir, "setup.py"))

    def run(self, *args, **kwargs):
        self.__locate_topdir()
        self.compilecount = 0
        return BaseTestCase.run(self, *args, **kwargs)

    def compile(self, input):
        self.compilecount += 1
        input = SourceReader('# 1 "<testcase>"\n' + input)
        output = stringio.StringIO()
        tree = compiler.compile(input.readline, output.write)
        return tree, TestOutput(self, self.compilecount, output.getvalue())

    def disable_loggers(self):
        for logger in compiler.loggers.values():
            logger.disable()

    def collect_blocks(self, function):
        result = {}
        self.__collect_blocks(result, function.entry_block)
        return result

    def __collect_blocks(self, result, block):
        if not result.has_key(block.index):
            result[block.index] = block
            for block in block.exits:
                self.__collect_blocks(result, block)

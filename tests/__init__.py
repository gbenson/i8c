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
from __future__ import unicode_literals

from i8c.compiler import commands
from i8c import compiler
from i8c import runtime
from i8c import version
from i8c.compiler import target
from i8c.runtime.testcase import BaseTestCase
import io
import os
import struct
import subprocess

class SourceReader(io.BytesIO):
    def readline(self):
        line = io.BytesIO.readline(self)
        trim = line.find(b"//")
        if trim >= 0:
            line = line[:trim] + b"\n"
        return line

class TestOutput(runtime.Context):
    def __init__(self, testcase, index, asm):
        runtime.Context.__init__(self)
        self.__set_fileprefix(testcase, index)
        # Store the assembly language we generated
        asmfile = self.fileprefix + ".S"
        with open(asmfile, "wb") as fp:
            fp.write(asm)
        # Assemble it
        objfile = self.fileprefix + ".o"
        subprocess.check_call(
            commands.I8C_CC + ["-c", asmfile, "-o", objfile])
        # Load the notes from it
        self.import_notes(objfile)
        self.notes = []
        for notes in self.functions.values():
            self.notes.extend(notes)
        # Make sure we got at least one note
        testcase.assertGreaterEqual(len(self.notes), 1)
        # Setup for note execution
        self.env = testcase
        self.memory = testcase.memory
        self.memory.env = self
        self.register_symbol = testcase.register_symbol

    def __set_fileprefix(self, testcase, index):
        test_id = testcase.id().split(".")
        # Remove the common prefix and the name of the class
        assert test_id[0] == "tests"
        test_id.pop(0)
        test_id.pop(-2)
        # Build the result
        index = "_%04d" % index
        self.fileprefix = os.path.join(
            testcase.topdir, "tests", "output", *test_id) + index
        # Ensure the directory we'll write to exists
        dir = os.path.dirname(self.fileprefix)
        if not os.path.exists(dir):
            os.makedirs(dir)

    # See contrib/libi8x-testnote-export.py
    if os.environ.get("LIBI8X_TESTNOTE_EXPORT", "0") == "1":
        def __split_note_filename(self, filename):
            prefix = os.path.splitext(filename)[0]
            assert prefix == self.fileprefix
            prefix, testfunc = os.path.split(prefix)
            testfunc = testfunc.split("_")
            index = testfunc.pop()
            testfunc = "_".join(testfunc)
            prefix, pyfile = os.path.split(prefix)
            assert os.path.basename(prefix) == "output"
            return prefix, pyfile, testfunc, index

        def import_note(self, note):
            # First actually import the note
            runtime.Context.import_note(self, note)
            # Now decide where we'll save it
            prefix, pyfile, testfunc, index \
                = self.__split_note_filename(note.filename)
            self.export_count = getattr(self, "export_count", 0) + 1
            dir = os.path.join(
                prefix, "for-libi8x", "i8c", version(),
                "%d%s" % (self.wordsize,
                          {b"<": "el", b">": "be"}[self.byteorder]),
                pyfile, testfunc)
            filename = os.path.join(dir,
                                    "%s-%04d" % (index, self.export_count))
            # Now save it
            if not os.path.exists(dir):
                os.makedirs(dir)
            with open(filename, "wb") as fp:
                fp.write(note.bytes)

    @property
    def note(self):
        assert len(self.notes) == 1
        return self.notes[0]

    @property
    def ops(self):
        ops = sorted(self.note.ops.items())
        return [op for pc, op in ops]

    @property
    def opnames(self):
        return [op.name for op in self.ops]

class TestCase(BaseTestCase):
    _wordsize = target.guess_wordsize()

    def __locate_topdir(self):
        self.topdir = os.path.realpath(__file__)
        self.topdir, check = os.path.split(self.topdir)
        assert check.startswith("__init__.py")
        self.topdir, check = os.path.split(self.topdir)
        assert check == "tests"
        assert os.path.exists(os.path.join(self.topdir, "setup.py"))

    def run(self, *args, **kwargs):
        self.__locate_topdir()
        self.compilecount = 0
        return BaseTestCase.run(self, *args, **kwargs)

    def compile(self, input):
        self.compilecount += 1
        for line in input.split("\n"):
            if line.lstrip().startswith("wordsize "):
                break
        else:
            input = "wordsize %d\n%s" % (self._wordsize, input)
        input = SourceReader(b'# 1 "<testcase>"\n' + input.encode("utf-8"))
        output = io.BytesIO()
        tree = compiler.compile(input.readline, output.write)
        return tree, TestOutput(self, self.compilecount, output.getvalue())

    def disable_loggers(self):
        for logger in compiler.loggers.values():
            logger.disable()

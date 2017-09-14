# -*- coding: utf-8 -*-
# Copyright (C) 2015-17 Red Hat, Inc.
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
from i8c.runtime import coverage
from i8c.runtime.testcase import BaseTestCase
import io
import os
import struct
import subprocess
import sys
import weakref

class SourceReader(io.BytesIO):
    def readline(self):
        line = io.BytesIO.readline(self)
        trim = line.find(b"//")
        if trim >= 0:
            line = line[:trim] + b"\n"
        return line

class TestOutput(runtime.Context):
    def __init__(self, env, fileprefix):
        self.__XXX_env = weakref.ref(env)
        self._Context__ctx = None            # XXX
        self._Context__extra_checks = False  # XXX
        self.fileprefix = fileprefix

    def add_variant(self, syntax_tree, asm):
        testcase = self.__XXX_env()
        del self.__XXX_env, self._Context__ctx, self._Context__extra_checks
        runtime.Context.__init__(self, testcase)
        testcase.addCleanup(self.finalize)
        self.syntax_tree = syntax_tree
        # Ensure the directory we'll write to exists
        outdir = os.path.dirname(self.fileprefix)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        # Store the assembly language we generated
        asmfile = self.fileprefix + ".S"
        with open(asmfile, "wb") as fp:
            fp.write(asm)
        # Assemble it
        objfile = self.fileprefix + ".o"
        subprocess.check_call(
            commands.I8C_CC + ["-c", asmfile, "-o", objfile])
        # Load the notes from it
        self.coverage = coverage.Accumulator()
        self.import_error = None
        testcase.addCleanup(delattr, self, "import_error")
        try:
            self.import_notes(objfile)
        except runtime.UnhandledNoteError as e:
            self.import_error = e
            return
        self.notes = list(self._i8ctest_functions)
        testcase.addCleanup(delattr, self, "notes")
        # Make sure we got at least one note
        testcase.assertGreaterEqual(len(self.notes), 1)
        # Setup for note execution
        testcase.memory.env = self
        self.register_symbol = testcase.register_symbol
        testcase._install_user_functions(self)
        testcase.to_signed = self.to_signed
        testcase.to_unsigned = self.to_unsigned

    @property
    def variants(self):
        return (self,)

    # TestCase.compile historically returned a two-element tuple
    # of (AST, TestOutput).  Defining __iter__ like this allows
    # TestCase.compile to return just TestOutput without having
    # to adjust all the tests.
    def __iter__(self):
        return iter((self.syntax_tree, self))

    @property
    def note(self):
        if self.import_error is not None:
            raise self.import_error
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
    __i8c_testcase__ = True

    topdir = os.path.realpath(__file__)
    topdir, check = os.path.split(topdir)
    assert check.startswith("__init__.py")
    topdir, module = os.path.split(topdir)
    assert os.path.exists(os.path.join(topdir, "setup.py"))
    del check
    assert os.getcwd() == topdir

    target_wordsize = target.guess_wordsize()
    assert target_wordsize is not None

    backend = TestOutput.INTERPRETER
    print("using", backend, file=sys.stderr)
    backend = backend.split(None, 1)[0].lower()

    def run(self, *args, **kwargs):
        self.compilecount = 0
        for logger in compiler.loggers.values():
            logger.disable()
        return BaseTestCase.run(self, *args, **kwargs)

    def _new_compilation(self):
        """Update compilation count and return a new TestOutput.
        """
        tmp = self.id().split(".")
        self.assertEqual(tmp[0], self.module)
        self.assertTrue(tmp.pop(-2).startswith("Test"))
        tmp.insert(1, "output")

        self.compilecount += 1
        fileprefix = os.path.join(*tmp) + "_%04d" % self.compilecount
        return TestOutput(self, fileprefix)

    def compile(self, input):
        """Compile I8Language to object code, then load resulting notes.

        Returns a tuple, the first element of which is the syntax tree
        after I8C has run, and the second element of which is a context
        with all notes from the generated object code loaded.
        """
        result = self._new_compilation()
        for line in input.split("\n"):
            if line.lstrip().startswith("wordsize "):
                break
        else:
            input = "wordsize %d\n%s" % (self.target_wordsize, input)
        input = SourceReader(b'# 1 "<testcase>"\n' + input.encode("utf-8"))
        output = io.BytesIO()
        tree = compiler.compile(input.readline, output.write)
        result.add_variant(tree, output.getvalue())
        return result

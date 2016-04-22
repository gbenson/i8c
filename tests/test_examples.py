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

from tests import TestCase
from i8c import compiler
from i8c import runtime
import os
import sys

class TestExamples(TestCase):
    def setUp(self):
        # Locate the directories
        self.__examples = os.path.join(self.topdir, "examples")
        self.__output = os.path.join(self.topdir, "tests",
                                     "output", "test_examples")
        if not os.path.exists(self.__output):
            os.makedirs(self.__output)
        # Create a list of files to delete
        self.__unlink_me = []
        # Save whatever sys.argv is
        self.__saved_argv = sys.argv
        # Pipe stdout and stderr to files
        self.__streams = {}
        for name in "stdout", "stderr":
            stream = getattr(sys, name)
            try:
                fileno = stream.fileno()
            except:
                # Already captured by nosetests?
                continue
            outfile = os.path.join(self.__output, name)
            if os.path.exists(outfile):
                os.unlink(outfile)
            new_fd = os.open(outfile,
                             os.O_RDWR | os.O_CREAT | os.O_EXCL,
                             0o600)
            stream.flush()
            saved_fd = os.dup(fileno)
            os.dup2(new_fd, fileno)

            self.__streams[name] = outfile, stream, saved_fd, new_fd

    def tearDown(self):
        # Restore stdout and stderr
        for outfile, stream, saved_fd, new_fd in self.__streams.values():
            stream.flush()
            os.dup2(saved_fd, stream.fileno())
            os.close(saved_fd)
            os.close(new_fd)
        # Restore sys.argv
        sys.argv = self.__saved_argv
        # Delete anything we created in funny places
        for filename in self.__unlink_me:
            if os.path.exists(filename):
                os.unlink(filename)

    def test_factorial(self):
        """Test that the factorial example works."""
        factdir = os.path.join(self.__examples, "factorial")

        source = os.path.join(factdir, "factorial.i8")
        objfile = os.path.join(factdir, "factorial.o")
        testfile = os.path.join(factdir, "test-factorial.py")

        self.__unlink_me.append(objfile)

        # Run the exact commands in the documentation
        sys.argv[1:] = ["-c", source]
        self.assertIs(compiler.main(), None)
        sys.argv[1:] = ["-i", objfile, "-q", "example::factorial(i)i", "12"]
        self.assertIs(runtime.main(), None)
        sys.argv[1:] = ["-i", objfile, testfile]
        self.assertIs(runtime.main(), None)

        # Check nothing was output to stderr
        sys.stderr.flush()
        errors = open(self.__streams["stderr"][0]).read()
        self.assertEqual(errors, "")

        # Check the output of the two I8X invocations
        if hasattr(sys.stdout, "getvalue"):
            # Captured by nosetests
            output = sys.stdout.getvalue()
        else:
            # Captured by us
            sys.stdout.flush()
            output = open(self.__streams["stdout"][0]).read()
        lines = output.split("\n")
        self.assertEqual(lines[0], "479001600")
        self.assertTrue(lines[-4].startswith("Ran 1 test in "))
        self.assertEqual(lines[-2], "OK")

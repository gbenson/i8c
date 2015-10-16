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
from __future__ import unicode_literals

from tests import TestCase
from i8c.compiler import I8CError
from i8c.compiler.driver import main
import os
import subprocess
import sys
import tempfile

SOURCE = """\
define test::func
    return
"""

class TestCompilerDriver(TestCase):
    """Test i8c.compiler.driver.main.

    This testcase should be the bare minumum to exercise the function
    i8c.compiler.driver.main and its helper functions.  Command line
    processing tests should be in test_commandline_processor.py, and
    tests exercising the compiler generally (i8c.compiler.compile)
    should be in their own files.
    """

    def setUp(self):
        # Set up a working directory
        self.workdir = tempfile.mkdtemp()
        self.filebase = os.path.join(self.workdir, "test")
        self.infile = self.filebase + ".i8"
        with open(self.infile, "w") as fp:
            fp.write(SOURCE)
        # Pipe stderr to a file
        tmpfile = os.path.join(self.workdir, "stderr")
        self.stderr_fd = os.open(tmpfile,
                                 os.O_RDWR | os.O_CREAT | os.O_EXCL,
                                 0o600)
        sys.stderr.flush()
        self.saved_stderr_fd = os.dup(2)
        os.dup2(self.stderr_fd, 2)

    def tearDown(self):
        # Restore stderr
        sys.stderr.flush()
        os.dup2(self.saved_stderr_fd, 2)
        os.close(self.saved_stderr_fd)
        os.close(self.stderr_fd)
        # Delete the working directory
        os.chmod(self.workdir, 0o700)
        subprocess.call(("rm", "-rf", self.workdir))

    # Test all specifiable permutations of (with_cpp,with_i8c,with_asm)

    def __run_permtest(self, args, outext):
        self.outfile = self.filebase + outext
        if outext != ".o":
            args.extend(("-o", self.outfile))
        args.append(self.infile)
        self.assertFalse(os.path.exists(self.outfile))
        status = main(args)
        self.assertIs(status, None)
        self.assertTrue(os.path.isfile(self.outfile))
        junk = os.path.join(self.workdir, "-.o")
        self.assertFalse(os.path.exists(junk))

    def test_do_nothing(self):
        """Check that -E -fpreprocessed is rejected."""
        self.assertRaises(I8CError, main, ["-E", "-fpreprocessed"])

    def test_pp_to_asm(self):
        """Check that preprocessed source to assembly works."""
        self.__run_permtest(["-S", "-fpreprocessed"], ".S")

    def test_pp_to_obj(self):
        """Check that preprocessed source to object code works."""
        self.__run_permtest(["-fpreprocessed", "-c"], ".o")

    def test_i8_to_pp(self):
        """Check that i8 source to preprocessed source works."""
        self.__run_permtest(["-E"], ".i8p")

    def test_i8_to_asm(self):
        """Check that i8 source to assembly works."""
        self.__run_permtest(["-S"], ".S")

    def test_i8_to_obj(self):
        """Check that i8 source to object code works."""
        self.__run_permtest(["-c"], ".o")

    # Test that GCC errors are handled correctly

    def __run_failtest(self):
        status = main(["-c", self.infile])
        self.assertIsNot(status, None)
        size = os.lseek(self.stderr_fd, 0, 1)
        os.lseek(self.stderr_fd, 0, 0)
        output = os.read(self.stderr_fd, size).decode("utf-8")
        self.assertGreaterEqual(output.find("error:"), 0)

    def test_cpp_failure(self):
        """Check that preprocessor errors are handled correctly."""
        os.unlink(self.infile)
        self.__run_failtest()

    def test_asm_failure(self):
        """Check that assembler errors are handled correctly."""
        os.chmod(self.workdir, 0o500)
        self.__run_failtest()

    # Test that multiple input files with no output file is caught

    def test_multi_input_no_output(self):
        """Check that unguessable output filenames are handled."""
        infile2 = os.path.join(self.workdir, "test2.i8")
        open(infile2, "w")
        self.assertRaises(I8CError,
                          self.__run_permtest, ["-c", infile2], ".o")

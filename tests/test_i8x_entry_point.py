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
from i8c.runtime import main
import sys

class TestEntryPoint(TestCase):
    """Test i8c.runtime.main, the console scripts entry point.

    This testcase should be the bare minimum required to exercise
    i8c.runtime.main.  Tests exercising the function it wraps
    (i8c.runtime.driver.main) should be in test_runtime_driver.py
    so they may be run without messing with sys.argv and sys.stderr.
    """

    def setUp(self):
        self.saved_argv = sys.argv
        self.saved_stderr = sys.stderr

    def tearDown(self):
        sys.argv = self.saved_argv
        sys.stderr = self.saved_stderr

    def test_success_path(self):
        """Check the i8x console scripts entry point success path."""
        sys.argv[1:] = ["--version"]
        self.assertIs(main(), None)

    def test_failure_path(self):
        """Check the i8x console scripts entry point failure path."""
        sys.argv[1:] = ["--kjhkjsadx"]
        sys.stderr = sys.stdout
        self.assertEqual(main(), 1)

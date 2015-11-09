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
from i8c.compiler import ParserError

SOURCE = """\
define test::test_toplevel_extern returns int
    argument ptr p
    call a_function
"""

SOURCE1 = """\
extern func int, int (ptr) %s
""" + SOURCE

SOURCE2 = """\
typedef func int, int (ptr) functype
extern functype %s
""" + SOURCE

class TestTopLevelExtern(TestCase):
    def test_basic(self):
        """Check that basic toplevel externals work."""
        self.__test_good(SOURCE1)

    def test_typedef(self):
        """Check that typedef toplevel externals work."""
        self.__test_good(SOURCE2)

    def __test_good(self, source):
        tree, output = self.compile(source % "test::a_function")
        self.assertEqual(["load_external", "call"], output.opnames)

    def test_basic_no_prov(self):
        """Check basic toplevel externals without providers fail."""
        self.__test_no_prov(SOURCE1)

    def test_typedef_no_prov(self):
        """Check typedef toplevel externals without providers fail."""
        self.__test_no_prov(SOURCE2)

    def __test_no_prov(self, source):
        self.assertRaises(ParserError, self.compile, source % "a_function")

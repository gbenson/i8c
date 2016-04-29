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
from i8c.compiler import ParserError

FUNCSRC = """\
define test::test_toplevel_extern_func returns int
    argument ptr p
    call a_function
"""

FUNCSRC1 = """\
extern func int, int (ptr) %s
""" + FUNCSRC

FUNCSRC2 = """\
typedef func int, int (ptr) functype
extern functype %s
""" + FUNCSRC

class TestTopLevelExtFunc(TestCase):
    def test_basic(self):
        """Check that basic toplevel external functions work."""
        self.__test_good(FUNCSRC1)

    def test_typedef(self):
        """Check that typedef toplevel external functions work."""
        self.__test_good(FUNCSRC2)

    def __test_good(self, source):
        tree, output = self.compile(source % "test::a_function")
        self.assertEqual(["load_external", "call"], output.opnames)

    def test_basic_no_prov(self):
        """Check basic toplevel external functions without providers fail."""
        self.__test_no_prov(FUNCSRC1)

    def test_typedef_no_prov(self):
        """Check typedef toplevel external functions without providers fail."""
        self.__test_no_prov(FUNCSRC2)

    def __test_no_prov(self, source):
        self.assertRaises(ParserError, self.compile, source % "a_function")


SYMSRC = """\
define test::test_toplevel_extern_sym returns ptr
    load a_symbol
"""

SYMSRC1 = """\
extern ptr %s
""" + SYMSRC

SYMSRC2 = """\
typedef ptr symtype
extern symtype %s
""" + SYMSRC

class TestTopLevelExtSym(TestCase):
    def test_basic(self):
        """Check that basic toplevel symbols work."""
        self.__test_good(SYMSRC1)

    def test_typedef(self):
        """Check that typedef toplevel symbols work."""
        self.__test_good(SYMSRC2)

    def __test_good(self, source):
        tree, output = self.compile(source % "a_symbol")
        self.assertEqual(["addr"], output.opnames)

    def test_basic_with_prov(self):
        """Check basic toplevel symbols with providers fail."""
        self.__test_with_prov(SYMSRC1)

    def test_typedef_with_prov(self):
        """Check typedef toplevel symbols with providers fail."""
        self.__test_with_prov(SYMSRC2)

    def __test_with_prov(self, source):
        self.assertRaises(ParserError, self.compile,
                          source % "test::a_symbol")



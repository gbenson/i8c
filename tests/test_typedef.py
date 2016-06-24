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
from i8c.compiler import RedefinedIdentError
from i8c.compiler import UndefinedIdentError

UNDEF_SOURCE = """\
define test::test_typedef returns the_type
    argument the_type x
"""

VALID_SOURCE = """\
typedef int the_type
""" + UNDEF_SOURCE

REDEF_SOURCE = """\
typedef ptr the_type
""" + VALID_SOURCE

class TestTypedef(TestCase):
    """Check that undefined and duplicate types are caught."""

    def test_valid(self):
        """Basic check of a valid typedef."""
        tree, output = self.compile(VALID_SOURCE)
        self.assertEqual([], output.opnames)

    def test_undefined(self):
        """Check that references to undefined types are caught."""
        self.assertRaises(UndefinedIdentError, self.compile, UNDEF_SOURCE)

    def test_redefined(self):
        """Check that duplicate typedefs are inhibited."""
        self.__test_redefined(REDEF_SOURCE)
        for builtin in ("int", "ptr", "opaque", "bool", "int32_t", "uint64_t"):
            self.__test_redefined("typedef uint8_t " + builtin)

    def __test_redefined(self, source):
        self.assertRaises(RedefinedIdentError, self.compile, source)

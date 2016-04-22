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
from i8c.compiler import StackError

SOURCE = """\
define test::unary_ops_test
    argument %s arg
    %s
"""

class TestUnaryOperations(TestCase):
    OPERATIONS = "abs", "neg", "not"

    def test_int_arg(self):
        """Check that unary operations work with int arguments."""
        for type in ("int", "bool"):
            for op in self.OPERATIONS:
                tree, output = self.compile(SOURCE % (type, op))
                self.assertEqual([op], output.opnames)

    def test_nonint_arg(self):
        """Check unary operations with non-int arguments are rejected."""
        for type in ("ptr", "opaque", "func ()"):
            for op in self.OPERATIONS:
                self.assertRaises(StackError, self.compile,
                                  SOURCE % (type, op))

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

SOURCE = """\
define test::optimize_use_plus_uconst returns int
    argument int x

    load %s
    add
"""

class TestOptimizeUsePlusUconst(TestCase):
    def test_optimize_use_plus_uconst(self):
        """Check that DW_OP_plus_uconst is used where possible."""
        for value in ("TRUE", 5, 255, 16384, 327889, 123456789):
            tree, output = self.compile(SOURCE % value)
            ops = output.ops
            self.assertEqual(len(ops), 1)
            self.assertEqual(ops[0].name, "plus_uconst")
            self.assertEqual(ops[0].operand, value == "TRUE" and 1 or value)

    def test_optimize_dont_use_plus_uconst_neg(self):
        """Check that DW_OP_plus_uconst is not used for negative numbers."""
        for value in (-1, -5, -255, -16384, -327889, -123456789):
            tree, output = self.compile(SOURCE % value)
            ops = output.ops
            self.assertEqual(len(ops), 2)
            self.assertEqual(ops[0].operand, value)
            self.assertEqual(ops[1].name, "plus")

    def test_optimize_dont_use_plus_uconst_zero(self):
        """Check that DW_OP_plus_uconst is not used for zero."""
        for value in (0, "FALSE"):
            tree, output = self.compile(SOURCE % value)
            self.assertEqual(len(output.ops), 0)
        tree, output = self.compile(SOURCE.replace("int", "ptr") % value)
        self.assertEqual(len(output.ops), 0)

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
define test::comparison_test
    argument %s arg_1
    argument %s arg_2

    %s
label:
"""

class TestComparisons(TestCase):
    OPERATIONS = "lt", "le", "eq", "ne", "ge", "gt"
    TYPES = "int", "bool", "ptr", "opaque", "func ()"

    def test_comparisons(self):
        """Basic checks for compare and compare+branch bytecodes."""
        for prefix, suffix in (("", ""), ("b", " label")):
            for op in self.OPERATIONS:
                for type1 in self.TYPES:
                    for type2 in self.TYPES:
                        expect_ops = [op]
                        if prefix == "b":
                            expect_ops.append("bra")
                        self.__run_test(SOURCE % (type1, type2,
                                                  prefix + op + suffix),
                                        self.__expect_success(type1, type2),
                                        expect_ops)

    def __expect_success(self, type1, type2):
        if type1 == "ptr" and type2 == "ptr":
            return True
        if type1 in ("int", "bool") and type2 in ("int", "bool"):
            return True
        return False

    def __run_test(self, source, expect_success, expect_ops):
        if expect_success:
            tree, output = self.compile(source)
            self.assertEqual(expect_ops, output.opnames)
        else:
            self.assertRaises(StackError, self.compile, source)

# -*- coding: utf-8 -*-
# Copyright (C) 2016 Red Hat, Inc.
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

class TestOptimizeMath(TestCase):
    def __test(self, input_op, input_values, expect_ops, expect_out=None):
        source = ("define test::opt_const_math returns int\n"
                  + "load %d\n" * len(input_values)
                  + input_op)
        tree, output = self.compile(source % tuple(input_values))
        self.assertEqual(expect_ops, output.opnames)
        if expect_out is not None:
            actual_out = output.call(output.note.signature)
            self.assertEqual(len(actual_out), 1)
            actual_out = output.to_signed(actual_out[0])
            self.assertEqual(actual_out, expect_out)

    def test_opt_const_add(self):
        """Check that constant add operations are optimized away."""
        self.__test("add", [14, 2], ["lit16"], 16)
        self.__test("add", [14, -2], ["lit12"], 12)
        self.__test("add", [23, -64], ["const1s"], -41)

    def test_opt_const_mul(self):
        """Check that constant mul operations are optimized away."""
        self.__test("mul", [14, 2], ["lit28"], 28)
        self.__test("mul", [14, -2], ["const1s"], -28)

    def test_opt_const_neg(self):
        """Check that constant neg operations are optimized away."""
        self.__test("neg", [14], ["const1s"], -14)
        self.__test("neg", [-2], ["lit2"], 2)

    def test_opt_const_sub(self):
        """Check that constant sub operations are optimized away."""
        self.__test("sub", [14, 2], ["lit12"], 12)
        self.__test("sub", [14, -2], ["lit16"], 16)
        self.__test("sub", [23, -64], ["const1u"], 87)

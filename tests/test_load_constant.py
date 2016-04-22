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
from i8c.compiler import parser
from i8c.compiler.types import INTTYPE, PTRTYPE, BOOLTYPE

INPUT_TEST = """\
define test::input_test
    load 23
    load 023
    load 0x23
    load -17
    load -017
    load -0x17
    load NULL
    load TRUE
    load FALSE
"""

class TestLoadConstantInput(TestCase):
    def test_input(self):
        """Check that the input is parsed correctly.
        """
        tree, output = self.compile(INPUT_TEST)
        constants = []
        node = tree.one_child(parser.Function)
        node = node.one_child(parser.Operations)
        for op in node.children:
            self.assertIsInstance(op, parser.LoadOp)
            for node in op.children:
                self.assertIsInstance(node, parser.Constant)
                constants.append([node.type, node.value])
        self.assertEqual([[INTTYPE, 23],
                          [INTTYPE, 0o23],
                          [INTTYPE, 0x23],
                          [INTTYPE, -17],
                          [INTTYPE, -0o17],
                          [INTTYPE, -0x17],
                          [PTRTYPE, 0],
                          [BOOLTYPE, 1],
                          [BOOLTYPE, 0]], constants)

OUTPUT_TEST = (
    (0, "lit0"),
    (31, "lit31"),
    (32, "const1u"),
    (255, "const1u"),
    (256, "const2u"),
    (65535, "const2u"),
    (65536, "constu"),
    (2097151, "constu"),
    (2097152, "const4u"),
    (4294967295, "const4u"),
    (4294967296, "constu"),
    (562949953421311, "constu"),
    (562949953421312, "const8u"),
    (18446744073709551615, "const8u"),
    (18446744073709551616, "constu"),
    (-1, "const1s"),
    (-128, "const1s"),
    (-129, "const2s"),
    (-32768, "const2s"),
    (-32769, "consts"),
    (-1048576, "consts"),
    (-1048577, "const4s"),
    (-2147483648, "const4s"),
    (-2147483649, "consts"),
    (-281474976710656, "consts"),
    (-281474976710657, "const8s"),
    (-9223372036854775808, "const8s"),
    (-9223372036854775809, "consts"))

class TestLoadConstantOutput(TestCase):
    def test_output(self):
        """Check that the correct bytecodes are emitted.
        """
        for value, opname in OUTPUT_TEST:
            tree, output = self.compile(
                "define test::input_test\nload %d" % value)

            ops = output.ops
            self.assertEqual(len(ops), 1)
            op = ops[0]
            self.assertEqual(op.name, opname)
            if value < 0 or value > 31:
                self.assertEqual(op.operand, value)

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
from i8c import compat
from i8c.compiler import parser
from i8c.compiler import I8CError
from i8c.compiler import LexerError, ParserError
from i8c.compiler import UndefinedIdentError
from i8c.compiler.types import INTTYPE, PTRTYPE, BOOLTYPE

INPUTS = (
    ("0", INTTYPE),
    ("1", INTTYPE),
    ("8", INTTYPE),
    ("9", INTTYPE),

    ("12345", INTTYPE),
    ("01234", INTTYPE),
    ("0x123", INTTYPE),

    ("0o123", None), # Python style octal
    ("0b101", None),
    ("0n123", None),

    ("1a234", None),
    ("01a23", None),
    ("01823", None),
    ("0x1g4", None),

    ("0X123", INTTYPE),
    ("0O123", None),
    ("0B101", None),
    ("0N123", None),
    ("1A234", None),
    ("01A23", None),
    ("01823", None),
    ("0X1G4", None),

    ("NULL", PTRTYPE),
    ("TRUE", BOOLTYPE),
    ("FALSE", BOOLTYPE),

    ("NXLL", None),
    ("TXUE", None),
    ("FXLSE", None),

    ("Null", None),
    ("True", None),
    ("False", None),

    ("null", None),
    ("True", None),
    ("False", None),

    ("NONE", None),
    ("None", None),
    ("none", None))

SOURCE = """\
define test::input_test
    load %s
    drop
"""

class TestNumericConstant(TestCase):
    def test_numeric(self):
        """Check that numeric constants are parsed correctly.
        """
        for input, expect in INPUTS:
            for prefix in "", "-":
                self.__do_test(prefix + input, expect)

    def __do_test(self, input, expect):
        exception = ParserError
        if input.startswith("-"):
            if expect not in (None, INTTYPE):
                expect = None
            if not input[1].isdigit():
                exception = LexerError
        elif expect is None and not input[0].isdigit():
            exception = UndefinedIdentError

        source = SOURCE % input
        if expect is None:
            self.assertRaises(exception, self.compile, source)
            return

        tree, output = self.compile(source)
        node = tree.one_child(parser.Function)
        node = node.one_child(parser.Operations)

        self.assertEqual(len(node.children), 2)
        load, drop = node.children
        self.assertIsInstance(load, parser.LoadOp)
        self.assertIsInstance(drop, parser.SimpleOp)
        self.assertEqual(drop.name, "drop")

        self.assertEqual(len(load.children), 1)
        [node] = load.children
        self.assertIsInstance(node, parser.Constant)
        self.assertEqual(node.type, expect)

    def test_bad_octal(self):
        """Check that compat.strtoint_c catches bad octal.
        """
        for prefix in "", "-":
            for base in range(ord("a"), ord("z") + 1):
                base = chr(base)
                if base == "x":
                    continue
                for base in base.lower(), base.upper():
                    self.assertRaises(I8CError,
                                      compat.strtoint_c,
                                      "%s0%s0" % (prefix, base),
                                      I8CError)

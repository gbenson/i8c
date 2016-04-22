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
define test::binary_ops_test
    argument %s arg_1
    argument %s arg_2
    %s
"""

class TestBinaryOperations(TestCase):
    OPERATIONS = ("add", "and", "div", "mod", "mul", "or",
                  "shl", "shr", "shra", "sub", "xor")
    TYPES = "int", "bool", "ptr", "opaque", "func ()"

    def test_binary_ops(self):
        """Check that binary operations work."""
        for op in self.OPERATIONS:
            for type1 in self.TYPES:
                for type2 in self.TYPES:
                    self.__run_test(op, type1, type2)

    def __run_test(self, op, type1, type2):
        """Try and compile TYPE1 OP TYPE2."""
        source = SOURCE % (type1, type2, op)
        # NB Top of stack is TYPE2, second entry is TYPE1.
        if self.__expect_success(op, type1, type2):
            tree, output = self.compile(source)
            op = {"add": "plus", "sub": "minus"}.get(op, op)
            self.assertEqual([op], output.opnames)
        else:
            self.assertRaises(StackError, self.compile, source)

    def __expect_success(self, op, type1, type2):
        """Is TYPE1 OP TYPE2 a valid thing to do?"""
        t1int = type1 in ("int", "bool")
        t2int = type2 in ("int", "bool")
        if t1int and t2int:
            return True
        if (op == "add"
            and (t1int or t2int)
            and "ptr" in (type1, type2)):
            return True
        if (op == "sub"
            and t2int
            and type1 == "ptr"):
            return True
        return False

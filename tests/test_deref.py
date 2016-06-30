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
from i8c.compiler import ParserError, ParsedError, StackTypeError

SOURCE = """\
typedef ptr ptr_alias

define test::deref
    argument %s arg

    deref %s
"""

class TestDeref(TestCase):
    TYPES = ("ptr", "ptr_alias",
             "int", "bool",
             "opaque", "func ()", "func int (ptr)",
             "uint8_t", "uint16_t", "uint32_t", "uint64_t",
             "int8_t", "int16_t", "int32_t", "int64_t",
             "intptr_t", "uintptr_t")

    def test_deref(self):
        """Check that deref works."""
        for argtype in self.TYPES:
            argtype_is_ok = argtype.startswith("ptr")
            for rettype in self.TYPES:
                rettype_is_func = rettype.startswith("func")
                rettype_is_ok = (rettype.startswith("ptr")
                                 or rettype.endswith("_t"))

                source = SOURCE % (argtype, rettype)

                if rettype_is_func:
                    exception = ParserError
                elif not rettype_is_ok:
                    exception = ParsedError
                elif not argtype_is_ok:
                    exception = StackTypeError
                else:
                    exception = None

                if exception is not None:
                    self.assertRaises(exception, self.compile, source)
                    continue

                tree, output = self.compile(source)
                ops = output.ops
                self.assertEqual(len(ops), 1)
                op = ops[0]

                if rettype in ("ptr", "ptr_alias"):
                    self.assertEqual("deref", op.name)
                    continue

                self.assertEqual("deref_int", op.name)
                is_signed = rettype[0] != "u"
                if not is_signed:
                    rettype = rettype[1:]
                rettype = rettype[3:-2]
                if rettype == "ptr":
                    sizecode = self._wordsize
                else:
                    sizecode = int(rettype)
                self.assertNotEqual(sizecode, 0)
                if is_signed:
                    sizecode *= -1
                self.assertEqual(op.operand, sizecode)

# -*- coding: utf-8 -*-
# Copyright (C) 2015 Red Hat, Inc.
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
             "u8", "u16", "u32", "u64",
             "s8", "s16", "s32", "s64")

    def test_deref(self):
        """Check that deref works."""
        for argtype in self.TYPES:
            argtype_is_ok = argtype.startswith("ptr")
            for rettype in self.TYPES:
                rettype_is_func = rettype.startswith("func")
                rettype_is_ok = not (rettype_is_func or rettype == "opaque")
                rettype_is_sized = rettype[0] in "su"
                expect_sign_extension = rettype in ("s8", "s16", "s32")

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

                if not rettype_is_sized:
                    expect_ops = ["deref"]
                else:
                    expect_ops = ["deref_size"]

                if expect_sign_extension:
                    expect_ops.extend(("const1u", "dup", "dup",
                                       "shl", "swap", "shr"))
                    if rettype != "s32":
                        expect_ops.append("plus_uconst")
                    expect_ops.extend(("dup", "rot", "shl", "swap", "shra"))

                tree, output = self.compile(source)
                self.assertEqual(expect_ops, output.opnames)

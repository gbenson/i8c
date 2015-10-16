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
from i8c.compiler import ParserError, StackError

SOURCE = """\
typedef func ptr (int) derived_func_t
typedef ptr derived_ptr_t
typedef int derived_int_t
typedef opaque derived_opaque_t

define test::test_cast returns ptr
   argument int an_argument
"""

class TestCast(TestCase):
    def test_nocast_fails(self):
        """Check that the test code fails without a cast."""
        self.assertRaises(StackError, self.compile, SOURCE)

    def test_cast(self):
        """Check that cast works."""
        for type in ("int",              # cast to same type
                     "bool",             # upcast to builtin derived type
                     "derived_int_t",    # upcast to user-defined derived type
                     "s32",              # upcast to builtin sized type
                     "ptr",              # cast to unrelated builtin type
                     "derived_ptr_t",    # cast to unrelated derived type
                     "func ptr (int)",   # cast to function
                     "derived_func_t",   # cast to derived function type
                     "opaque",           # cast to opaque
                     "derived_opaque_t", # cast to derived opaque type
                     ):
            for slot in (0, "an_argument", 15, "no_such_slot"):
                source = SOURCE + "cast %s %s" % (slot, type)

                if (type in ("ptr", "derived_ptr_t")
                    and slot in (0, "an_argument")):
                    error = None
                elif type == "func ptr (int)":
                    error = ParserError
                else:
                    error = StackError

                if error is None:
                    tree, output = self.compile(source)
                else:
                    self.assertRaises(error, self.compile, source)

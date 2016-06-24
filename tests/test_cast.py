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
from i8c.compiler import InvalidCastError
from i8c.compiler import ParserError
from i8c.compiler import StackError
from i8c.compiler import UndefinedIdentError
from i8c.compiler import UnnecessaryCastError

SOURCE = """\
typedef func ptr (int) derived_func_t
typedef ptr derived_ptr_t
typedef int derived_int_t
typedef opaque derived_opaque_t

define test::test_cast returns %s
   argument %s an_argument
"""

TYPEGROUPS = (
    ("int",             # builtin
     "bool",            # builtin (derived)
     "int32_t",         # builtin (derived, sized)
     "derived_int_t"),  # user-defined (derived)

    ("ptr",             # builtin
     "derived_ptr_t"),  # user-defined (derived)

    ("opaque",              # builtin
     "derived_opaque_t"),   # user-defined (derived)

    ("func ptr (int)",  # builtin (function)
     "derived_func_t")) # user-defined (function, derived)

class TestCast(TestCase):
    TYPES = []
    CASTS = {}
    for group in TYPEGROUPS:
        for type1 in group:
            TYPES.append(type1)
            for type2 in group:
                CASTS[(type1, type2)] = True
    del group, type1, type2

    @classmethod
    def types_match(cls, type1, type2):
        return cls.CASTS.get((type1, type2), False)

    @classmethod
    def can_cast(cls, type1, type2):
        for ab in (("int", "ptr"), ("ptr", "int")):
            if (cls.types_match(type1, ab[0])
                  and cls.types_match(type2, ab[1])):
                return True
        return False

    def test_cast(self):
        """Check that cast works."""
        for rtype in self.TYPES:
            for ptype in self.TYPES:
                # Test without casting
                source = SOURCE % (rtype, ptype)
                if self.types_match(ptype, rtype):
                    error = None
                else:
                    error = StackError
                self.__do_test(source, error)

                # Test with a cast
                for slot in (0, "an_argument", 15, "no_such_slot"):
                    cast = "cast %s, %s" % (slot, rtype)
                    if rtype == "func ptr (int)":
                        error = ParserError
                    elif slot == 15:
                        error = StackError
                    elif slot == "no_such_slot":
                        error = UndefinedIdentError
                    elif self.types_match(ptype, rtype):
                        error = UnnecessaryCastError
                    elif self.can_cast(ptype, rtype):
                        error = None
                    else:
                        error = InvalidCastError
                    self.__do_test(source + cast, error)

    def __do_test(self, source, error):
        if error is None:
            tree, output = self.compile(source)
        else:
            self.assertRaises(error, self.compile, source)

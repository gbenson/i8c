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

FUNCTYPE = "func int (int)"
GOODTYPES1 = (FUNCTYPE,)
BADTYPES1 = ("int", "func (int)", "func int (ptr)",
             "func int (int, int)", "func int (int, func int (int))")

SOURCE1 = """\
define test::return_func_test returns %s
    extern func int (int) factorial
    load factorial
"""

ALIASTYPE = "factorial_ft"
GOODTYPES2 = GOODTYPES1 + (ALIASTYPE,)
BADTYPES2 = BADTYPES1

SOURCE2 = ["typedef %s %s" % (FUNCTYPE, ALIASTYPE)]
for index, badtype in zip(range(len(BADTYPES1)), BADTYPES1):
    alias = "wrong_%d" % (index + 1)
    SOURCE2.append("typedef %s %s" % (badtype, alias))
    BADTYPES2 += (alias,)
SOURCE2 = "\n".join(SOURCE2 + [SOURCE1])

class TestReturnFunc(TestCase):
    def __do_test(self, template, goodtypes, badtypes):
        for type in goodtypes + badtypes:
            source = template % type
            if type in goodtypes:
                self.compile(source)
            else:
                self.assertRaises(StackError, self.compile, source)

    def test_raw_return_func(self):
        """Test that returning a function works."""
        self.__do_test(SOURCE1, GOODTYPES1, BADTYPES1)

    def test_typedef_return_func(self):
        """Test that returning a function via a typedef works."""
        self.__do_test(SOURCE2, GOODTYPES2, BADTYPES2)

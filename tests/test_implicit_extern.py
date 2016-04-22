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

SOURCE = """\
define test::is_odd returns bool
    argument int x
    dup
    bne 0, recurse
    load FALSE
    return
recurse:
    sub 1
    call is_even

define test::is_even returns bool
    argument int x
    dup
    bne 0, recurse
    load TRUE
    return
recurse:
    sub 1
    call is_odd
"""

IS_ODD = "test::is_odd(i)i"
IS_EVEN = "test::is_even(i)i"

class TestImplicitExtern(TestCase):
    def test_implicit_extern(self):
        """Test that implicit externals work."""
        tree, output = self.compile(SOURCE)
        for func, input, expect in ((IS_ODD, 0, 0),
                                    (IS_ODD, 1, 1),
                                    (IS_EVEN, 0, 1),
                                    (IS_EVEN, 1, 0),
                                    (IS_ODD, 17, 1),
                                    (IS_EVEN, 23, 0),
                                    (IS_ODD, 38, 0),
                                    (IS_EVEN, 42, 1)):
            self.assertEqual(output.call(func, input), [expect])


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
from i8c.compiler import UndefinedIdentError, StackMergeError

# A basic iterative factorial function.
SOURCE_BASIC = """\
define test::factorial returns int
    argument int x

    load 1
    swap
    goto check

loop:
    dup
    rot
    mul
    swap
    load 1
    sub

check:
    dup
    load 1
    bgt loop
    drop
"""

# A broken version of SOURCE_BASIC which falls through to "check"
# with an extra element on the stack that should be caught by the
# merge.
SOURCE_BAD_DEPTH = """\
define test::factorial returns int
    argument int x

    load 1
    swap
    goto check

loop:
    dup
    rot
    mul
    swap
    load 1
    sub
    load NULL

check:
    dup
    load 1
    bgt loop
    drop
"""

# A broken version of SOURCE_BASIC which falls through to "check"
# with a pointer at the top of the stack instead of the expected
# integer that should be caught by the merge.
SOURCE_BAD_TYPE = """\
define test::factorial returns int
    argument int x

    load 1
    swap
    goto check

loop:
    dup
    rot
    mul
    swap
    load 1
    sub
    cast 0, ptr

check:
    dup
    load 1
    bgt loop
    drop
"""

# A broken version of SOURCE_BASIC that trys to use "load x" at
# the start of the loop.  The name "x" should have been removed by
# the merge as it does not exist when falling through to "check".
SOURCE_LOST_NAME = """\
define test::factorial returns int
    argument int x

    load 1
    swap
    goto check

loop:
    load x
    rot
    mul
    swap
    load 1
    sub

check:
    dup
    load 1
    bgt loop
    drop
"""

# A fixed version of SOURCE_LOST_NAME where the name "x" is restored
# at the end of the loop and so not removed by the merge.
SOURCE_GOT_NAME = """\
define test::factorial returns int
    argument int x

    load 1
    swap
    goto check

loop:
    load x
    rot
    mul
    swap
    load 1
    sub
    name 0, x

check:
    dup
    load 1
    bgt loop
    drop
"""

FACTORIALS = (
    (0, 1),
    (1, 1),
    (2, 2),
    (3, 6),
    (4, 24),
    (5, 120),
    (6, 720),
    (7, 5040),
    (8, 40320),
    (9, 362880),
    (10, 3628800),
    (11, 39916800),
    (12, 479001600))

class TestLoops(TestCase):
    def test_basic(self):
        """Check that loops work."""
        self.__test(SOURCE_BASIC)

    def test_bad_depth(self):
        """Check that merges with incorrect depth are caught."""
        self.__test(SOURCE_BAD_DEPTH, StackMergeError)

    def test_bad_type(self):
        """Check that merges with incorrect types are caught."""
        self.__test(SOURCE_BAD_TYPE, StackMergeError)

    def test_lost_name(self):
        """Check that merges with lost names are caught."""
        self.__test(SOURCE_LOST_NAME, UndefinedIdentError)

    def test_got_name(self):
        """Check that lost names can be restored."""
        self.__test(SOURCE_GOT_NAME)

    def __test(self, source, exception=None):
        if exception is None:
            tree, output = self.compile(source)
            sig = output.note.signature
            self.assertEqual(sig, "test::factorial(i)i")
            for input, expect in FACTORIALS:
                self.assertEqual(output.call(sig, input), [expect])
        else:
            self.assertRaises(exception, self.compile, source)

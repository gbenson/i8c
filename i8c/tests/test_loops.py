# -*- coding: utf-8 -*-
from i8c.tests import TestCase
from i8c.compiler import StackError, StackMergeError

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
    cast 0 ptr

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
    name 0 x

check:
    dup
    load 1
    bgt loop
    drop
"""

TESTS = (
    (SOURCE_BASIC, None),
    (SOURCE_BAD_DEPTH, StackMergeError),
    (SOURCE_BAD_TYPE, StackMergeError),
    (SOURCE_LOST_NAME, StackError),
    (SOURCE_GOT_NAME, None))

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
    def test_loops(self):
        """Test that loops work."""
        for source, exception in TESTS:
            if exception is not None:
                self.assertRaises(exception, self.compile, source)
                continue
            tree, output = self.compile(source)
            sig = output.note.signature
            self.assertEqual(sig, "test::factorial(i)i")
            for input, expect in FACTORIALS:
                self.assertEqual(output.call(sig, input), [expect])

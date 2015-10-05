# This file is an i8x testcase and cannot be run standalone

from i8c.runtime import TestCase

class TestFactorial(TestCase):
    TESTFUNC = "example::factorial(i)i"

    def test_factorial(self):
        """Test example::factorial"""
        for x, expect in ((0, 1), (1, 1), (12, 479001600)):
            result = self.i8ctx.call(self.TESTFUNC, x)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0], expect)

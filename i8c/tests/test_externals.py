from i8c.tests import TestCase

SOURCE = """\
define test::externals_test returns int
    extern ptr a_symbol
    extern func int, int (ptr) a_function
    call
    return
"""

class TestExternals(TestCase):
    def test_externals(self):
        """Check that externals work."""
        tree, output = self.compile(SOURCE)
        self.assertEqual(["GNU_i8call"], output.operations)

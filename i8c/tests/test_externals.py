from i8c.tests import TestCase

SOURCE1 = """\
define test::externals_test returns int
    extern ptr a_symbol
    extern func int, int (ptr) a_function
    call
"""

SOURCE2 = """\
typedef ptr ptr_alias_t
typedef func int, int (ptr) fun_alias_f

define test::externals_test returns int
    extern ptr_alias_t a_symbol
    extern fun_alias_f a_function
    call
"""

class TestExternals(TestCase):
    def test_externals(self):
        """Check that externals work."""
        for source in SOURCE1, SOURCE2:
            tree, output = self.compile(source)
            self.assertEqual(["GNU_i8call"], output.opnames)

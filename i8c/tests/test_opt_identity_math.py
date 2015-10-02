from i8c.tests import TestCase

SOURCE = """\
define test::optimize_use_plus_uconst returns int
    argument int x

    load %s
    %s
"""

IDENTITIES = (("add", 0), ("sub", 0),
              ("mul", 1), ("div", 1),
              ("shl", 0), ("shr", 0),
              ("shra", 0), ("or", 0),
              ("xor", 0))

class TestEliminateIdentityMath(TestCase):
    def test_eliminate_identity_math(self):
        """Check that identity math and logic are eliminated."""
        for op, identity in IDENTITIES:
            tree, output = self.compile(SOURCE % (identity, op))
            self.assertEqual(len(output.ops), 0)

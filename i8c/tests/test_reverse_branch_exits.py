from i8c.tests import TestCase

SOURCE = """\
define test::optimize_reverse_branch_exits returns int
    argument int x

    load 1
    bne label1
    goto label2
label1:
    load 2
    return
label2:
    load 3
"""

class TestOptimizeReverseBranchExits(TestCase):
    def test_optimize_reverse_branch_exits(self):
        """Check we don't emit "bra, skip" if we don't need to."""
        tree, output = self.compile(SOURCE)
        self.assertEqual(["lit1", "eq", "bra",
                          "lit2", "skip",
                          "lit3"], output.opnames)

from i8c.tests import TestCase

TEST_SOURCE = """\
define test::stack_ops_test
    argument int arg_1
    argument ptr arg_2
    argument bool arg_3

    dup
    drop
    pick 0
    pick 1
    pick 2
    over
    swap
    rot
"""

class TestStackOperations(TestCase):
    def test_stack_ops(self):
        """Basic checks for stack-manipulation bytecodes."""
        tree, output = self.compile(TEST_SOURCE)
        # Check the assembler contains the expected operations
        self.assertEqual(["dup",
                          "drop",
                          "dup",    # pick 0
                          "over",   # pick 1
                          "pick",   # pick 2
                          "over",
                          "swap",
                          "rot"], output.operations)

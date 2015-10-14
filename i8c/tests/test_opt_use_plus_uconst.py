# -*- coding: utf-8 -*-
from i8c.tests import TestCase

SOURCE = """\
define test::optimize_use_plus_uconst returns int
    argument int x

    load %s
    add
"""

class TestOptimizeUsePlusUconst(TestCase):
    def test_optimize_use_plus_uconst(self):
        """Check that DW_OP_plus_uconst is used where possible."""
        for value in ("TRUE", 5, 255, 16384, 327889, 123456789):
            tree, output = self.compile(SOURCE % value)
            ops = output.ops
            self.assertEqual(len(ops), 1)
            self.assertEqual(ops[0].name, "plus_uconst")
            self.assertEqual(ops[0].operand, value == "TRUE" and 1 or value)

    def test_optimize_dont_use_plus_uconst_neg(self):
        """Check that DW_OP_plus_uconst is not used for negative numbers."""
        for value in (-1, -5, -255, -16384, -327889, -123456789):
            tree, output = self.compile(SOURCE % value)
            ops = output.ops
            self.assertEqual(len(ops), 2)
            self.assertEqual(ops[0].operand, value)
            self.assertEqual(ops[1].name, "plus")

    def test_optimize_dont_use_plus_uconst_zero(self):
        """Check that DW_OP_plus_uconst is not used for zero."""
        for value in (0, "FALSE"):
            tree, output = self.compile(SOURCE % value)
            self.assertEqual(len(output.ops), 0)
        tree, output = self.compile(SOURCE.replace("int", "ptr") % value)
        self.assertEqual(len(output.ops), 0)

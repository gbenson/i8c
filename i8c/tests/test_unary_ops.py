# -*- coding: utf-8 -*-
from i8c.tests import TestCase
from i8c.compiler import StackError

SOURCE = """\
define test::unary_ops_test
    argument %s arg
    %s
"""

class TestUnaryOperations(TestCase):
    OPERATIONS = "abs", "neg", "not"

    def test_int_arg(self):
        """Check that unary operations work with int arguments."""
        for type in ("int", "bool"):
            for op in self.OPERATIONS:
                tree, output = self.compile(SOURCE % (type, op))
                self.assertEqual([op], output.opnames)

    def test_nonint_arg(self):
        """Check unary operations with non-int arguments are rejected."""
        for type in ("ptr", "opaque", "func ()"):
            for op in self.OPERATIONS:
                self.assertRaises(StackError, self.compile,
                                  SOURCE % (type, op))

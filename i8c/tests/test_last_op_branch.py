# -*- coding: utf-8 -*-
from i8c.tests import TestCase

SOURCE = """\
define test::last_op_is_branch
    argument bool x
    argument bool y

    goto label2
label1:
    return

label2:
    bne label1
"""

class TestFuncWithLastOpBra(TestCase):
    def test_last_op_is_branch(self):
        """Check that functions whose last op is a branch work.

        This is testing the code that adds the synthetic return.
        As a side-effect it also exercises the code that stops
        us generating unnecessary gotos.
        """
        tree, output = self.compile(SOURCE)
        self.assertEqual(["ne", "bra"], output.opnames)

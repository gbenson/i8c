# -*- coding: utf-8 -*-
from i8c.tests import TestCase

SOURCE1 = """\
define test::optimize_cmp_bra_const_const returns ptr
    argument ptr x

    dup
    load NULL
    beq return_the_null
    deref ptr
    return
return_the_null:
"""

SOURCE2 = """\
define test::optimize_cmp_bra_const_const returns ptr
    argument ptr x

    dup
    load NULL
    bne dereference
    return
dereference:
    deref ptr
"""

class TestOptimizeLit0CmpBeforeBra(TestCase):
    def test_optimize_lit0_cmp_before_bra(self):
        """Check that lit0,cmp before bra is eliminated."""
        for source in SOURCE1, SOURCE2:
            tree, output = self.compile(source)
            self.assertEqual(["dup", "bra", "skip", "deref"], output.opnames)

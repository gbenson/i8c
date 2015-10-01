from i8c.tests import TestCase

# Simple testcase with only the load constant in the blocks
SIMPLE = """\
typedef int arg_type
typedef int ret_type

define test::optimize_cmp_bra_const_const returns ret_type
    argument arg_type arg1
    argument arg_type arg2

    b%s label

    // comparison returned 0
    load %s
    return

label:
    // comparison returned 1
    load %s
"""

# Harder testcase with an extra operation in each block
HARDER = """\
typedef int arg_type
typedef int ret_type

define test::optimize_cmp_bra_const_const returns ptr, ret_type
    argument ptr arg0
    argument arg_type arg1
    argument arg_type arg2

    b%s label

    // comparison returned 0
    load %s
    swap
    return

label:
    // comparison returned 1
    load %s
    swap
"""

class TestOptimizeCmpBraConstConst(TestCase):
    REVERSE = {"lt": "ge", "le": "gt", "eq": "ne",
               "ne": "eq", "ge": "lt", "gt": "le"}
    OPERATIONS = REVERSE.keys()
    OPERATIONS.sort()

    def test_optimize_cmp_bra_const_const(self):
        """Check that cmp-bra-{const,const} is optimized."""
        # bra is branch-if-NOT-zero
        for source, extra_ops in (SIMPLE, []), (HARDER, ["swap"]):
            for is_reversed, values in ((False, (0, 1)), (True, (1, 0))):
                for op in self.OPERATIONS:
                    tree, output = self.compile(source % ((op,) + values))
                    if is_reversed:
                        op = self.REVERSE[op]
                    self.assertEqual([op] + extra_ops, output.opnames)

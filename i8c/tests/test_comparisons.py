from i8c.tests import TestCase
from i8c.exceptions import StackError

SOURCE = """\
define test::comparison_test
    argument %s arg_1
    argument %s arg_2

    %s
label:
"""

class TestComparisons(TestCase):
    OPERATIONS = "lt", "le", "eq", "ne", "ge", "gt"
    TYPES = "int", "bool", "ptr", "opaque", "func ()"

    def test_comparisons(self):
        """Basic checks for compare and compare+branch bytecodes."""
        for prefix, suffix in (("", ""), ("b", " label")):
            for op in self.OPERATIONS:
                for type1 in self.TYPES:
                    for type2 in self.TYPES:
                        expect_ops = [op]
                        if prefix == "b":
                            expect_ops.append("bra")
                        self.__run_test(SOURCE % (type1, type2,
                                                  prefix + op + suffix),
                                        self.__expect_success(type1, type2),
                                        expect_ops)

    def __expect_success(self, type1, type2):
        if type1 == "ptr" and type2 == "ptr":
            return True
        if type1 in ("int", "bool") and type2 in ("int", "bool"):
            return True
        return False

    def __run_test(self, source, expect_success, expect_ops):
        if expect_success:
            tree, output = self.compile(source)
            self.assertEqual(expect_ops, output.operations)
        else:
            self.assertRaises(StackError, self.compile, source)

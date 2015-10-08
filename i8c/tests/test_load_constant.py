from i8c.tests import TestCase
from i8c.compiler import parser
from i8c.compiler.types import INTTYPE, PTRTYPE, BOOLTYPE

INPUT_TEST = """\
define test::input_test
    load 23
    load 023
    load 0x23
    load -17
    load -017
    load -0x17
    load NULL
    load TRUE
    load FALSE
"""

class TestLoadConstantInput(TestCase):
    def test_input(self):
        """Check that the input is parsed correctly.
        """
        tree, output = self.compile(INPUT_TEST)
        constants = []
        for op in tree.one_child(parser.Function).operations.children:
            self.assertIsInstance(op, parser.LoadOp)
            for node in op.children:
                self.assertIsInstance(node, parser.Constant)
                constants.append([node.type, node.value])
        self.assertEqual([[INTTYPE, 23],
                          [INTTYPE, 023],
                          [INTTYPE, 0x23],
                          [INTTYPE, -17],
                          [INTTYPE, -017],
                          [INTTYPE, -0x17],
                          [PTRTYPE, 0],
                          [BOOLTYPE, 1],
                          [BOOLTYPE, 0]], constants)

OUTPUT_TEST = (
    (0, "lit0"),
    (31, "lit31"),
    (32, "const1u"),
    (255, "const1u"),
    (256, "const2u"),
    (65535, "const2u"),
    (65536, "constu"),
    (2097151, "constu"),
    (2097152, "const4u"),
    (4294967295, "const4u"),
    (4294967296, "constu"),
    (562949953421311, "constu"),
    (562949953421312, "const8u"),
    (18446744073709551615, "const8u"),
    (18446744073709551616, "constu"),
    (-1, "const1s"),
    (-128, "const1s"),
    (-129, "const2s"),
    (-32768, "const2s"),
    (-32769, "consts"),
    (-1048576, "consts"),
    (-1048577, "const4s"),
    (-2147483648, "const4s"),
    (-2147483649, "consts"),
    (-281474976710656, "consts"),
    (-281474976710657, "const8s"),
    (-9223372036854775808, "const8s"),
    (-9223372036854775809, "consts"))

class TestLoadConstantOutput(TestCase):
    def test_output(self):
        """Check that the correct bytecodes are emitted.
        """
        for value, opname in OUTPUT_TEST:
            tree, output = self.compile(
                "define test::input_test\nload %d" % value)

            ops = output.ops
            self.assertEqual(len(ops), 1)
            op = ops[0]
            self.assertEqual(op.name, opname)
            if value < 0 or value > 31:
                self.assertEqual(op.operand, value)

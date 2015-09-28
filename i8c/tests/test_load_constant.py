from i8c.tests import TestCase
from i8c import parser
from i8c import types

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
        self.assertEqual([[types.INTTYPE, 23],
                          [types.INTTYPE, 023],
                          [types.INTTYPE, 0x23],
                          [types.INTTYPE, -17],
                          [types.INTTYPE, -017],
                          [types.INTTYPE, -0x17],
                          [types.PTRTYPE, 0],
                          [types.BOOLTYPE, 1],
                          [types.BOOLTYPE, 0]], constants)

OUTPUT_TEST = """\
define test::output_test
    load 0			// DW_OP_litN
    load 31
    load 32			// DW_OP_const1u
    load 255
    load 256			// DW_OP_const2u
    load 65535
    load 65536			// DW_OP_constu
    load 2097151
    load 2097152		// DW_OP_const4u
    load 4294967295
    load 4294967296		// DW_OP_constu (again)
    load 562949953421311
    load 562949953421312	// DW_OP_const8u
    load 18446744073709551615
    load 18446744073709551616	// DW_OP_constu (again)

    load -1			// DW_OP_const1s
    load -128
    load -129			// DW_OP_const2s
    load -32768
    load -32769			// DW_OP_consts
    load -1048576
    load -1048577		// DW_OP_const4s
    load -2147483648
    load -2147483649		// DW_OP_consts (again)
    load -281474976710656
    load -281474976710657	// DW_OP_const8s
    load -9223372036854775808
    load -9223372036854775809	// DW_OP_consts (again)
"""

class TestLoadConstantOutput(TestCase):
    def test_output(self):
        """Check that the correct bytecodes are emitted.
        """
        tree, output = self.compile(OUTPUT_TEST)
        self.assertEqual(["lit0", "lit31",
                          "const1u", "const1u",
                          "const2u", "const2u",
                          "constu", "constu",
                          "const4u", "const4u",
                          "constu", "constu",
                          "const8u", "const8u",
                          "constu",
                          "const1s", "const1s",
                          "const2s", "const2s",
                          "consts", "consts",
                          "const4s", "const4s",
                          "consts", "consts",
                          "const8s", "const8s",
                          "consts"], output.operations)

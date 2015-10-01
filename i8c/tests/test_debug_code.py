from i8c.tests import TestCase
from i8c.logger import loggers
import cStringIO as stringio
import sys

SOURCE = """\
define test::factorial returns int
    argument int x
    extern func int (int) factorial

    swap
    dup
    load 1
    bne not_done_yet
    return

not_done_yet:
    dup
    load 1
    sub
label: // ensure we hit the 1-exit case in blocks.Block.__str_
    swap
    rot
    swap
    call
    mul
"""

EXTERN0_NODE = """\
FuncRef
  FuncType [function int (int)]
    ReturnTypes
      BasicType: int [int]
    ParamTypes
      BasicType: int [int]
  ShortName: factorial"""

class TestDebugCode(TestCase):
    """Test various bits of debugging code."""

    def setUp(self):
        self.disable_loggers()
        self.saved_stderr = sys.stderr

    def tearDown(self):
        self.disable_loggers()
        sys.stderr = self.saved_stderr

    def test_loggers(self):
        """Exercise all the debug printers."""
        for logger in loggers.values():
            logger.enable()
        sys.stderr = stringio.StringIO()
        self.compile(SOURCE)

    def test_str_methods(self):
        """Check various __str__ methods."""
        tree, output = self.compile(SOURCE)
        func = list(tree.functions)[0]
        # lexer.Token.__str__
        token = func.operations.tokens[0]
        self.assertEqual(str(token), "<testcase>:5: u'swap'")
        # parser.TreeNode.__str__ with an annotated type
        node = func.externals.children[0]
        self.assertEqual(str(node), EXTERN0_NODE)
        # blocks.Block.__str_
        blocks = self.collect_blocks(func).items()
        blocks.sort()
        for index, block in blocks:
            self.assertTrue(str(block).startswith("Block #%d " % index))

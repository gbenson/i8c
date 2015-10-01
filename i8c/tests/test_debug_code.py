from i8c.tests import TestCase
from i8c.logger import loggers
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
    load 1
    sub
    swap
    call
"""

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
        sys.stderr = sys.stdout
        self.compile(SOURCE)

from i8c.tests import TestCase
from i8c.runtime import main
import sys

class TestEntryPoint(TestCase):
    """Test i8c.runtime.main, the console scripts entry point.

    This testcase should be the bare minimum required to exercise
    i8c.runtime.main.  Tests exercising the function it wraps
    (i8c.runtime.driver.main) should be in test_runtime_driver.py
    so they may be run without messing with sys.argv and sys.stderr.
    """

    def setUp(self):
        self.saved_argv = sys.argv
        self.saved_stderr = sys.stderr

    def tearDown(self):
        sys.argv = self.saved_argv
        sys.stderr = self.saved_stderr

    def test_success_path(self):
        """Check the i8x console scripts entry point success path."""
        sys.argv[1:] = ["--version"]
        self.assertIs(main(), None)

    def test_failure_path(self):
        """Check the i8x console scripts entry point failure path."""
        sys.argv[1:] = ["--kjhkjsadx"]
        sys.stderr = sys.stdout
        self.assertEqual(main(), 1)

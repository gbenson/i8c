from i8c.tests import TestCase

SOURCE = "define test::pretty_minimal"

class TestEmptyFunction(TestCase):
    def test_empty_function(self):
        """Check that empty functions can be compiled."""
        tree, output = self.compile(SOURCE)
        self.assertEqual([], output.opnames)

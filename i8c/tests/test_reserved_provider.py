from i8c.tests import TestCase
from i8c.exceptions import NameAnnotatorError

SOURCE = """\
define %s::test_reserved_provider returns ptr
    extern ptr __some_symbol
"""

class TestReservedProvider(TestCase):
    """Check that reserved provider names are rejected."""

    def test_reserved_provider(self):
        """Check that reserved provider names are rejected."""
        for provider in ("test", "libpthread", "i8test",
                         "i8core", "i8", "hello"):
            source = SOURCE % provider
            if provider.startswith("i8"):
                self.assertRaises(NameAnnotatorError, self.compile, source)
            else:
                tree, output = self.compile(source)
                self.assertEqual([], output.opnames)

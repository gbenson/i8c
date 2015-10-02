from i8c.tests import TestCase
from i8c.exceptions import StackError

FUNCTYPE = "func int (int)"
GOODTYPES1 = (FUNCTYPE,)
BADTYPES1 = ("int", "func (int)", "func int (ptr)",
             "func int (int, int)", "func int (int, func int (int))")

SOURCE1 = """\
define test::return_func_test returns %s
    extern func int (int) factorial
"""

ALIASTYPE = "factorial_ft"
GOODTYPES2 = GOODTYPES1 + (ALIASTYPE,)
BADTYPES2 = BADTYPES1

SOURCE2 = ["typedef %s %s" % (FUNCTYPE, ALIASTYPE)]
for index, badtype in zip(range(len(BADTYPES1)), BADTYPES1):
    alias = "wrong_%d" % (index + 1)
    SOURCE2.append("typedef %s %s" % (badtype, alias))
    BADTYPES2 += (alias,)
SOURCE2 = "\n".join(SOURCE2 + [SOURCE1])

class TestReturnFunc(TestCase):
    def __do_test(self, template, goodtypes, badtypes):
        for type in goodtypes + badtypes:
            source = template % type
            if type in goodtypes:
                self.compile(source)
            else:
                self.assertRaises(StackError, self.compile, source)

    def test_raw_return_func(self):
        """Test that returning a function works."""
        self.__do_test(SOURCE1, GOODTYPES1, BADTYPES1)

    def test_typedef_return_func(self):
        """Test that returning a function via a typedef works."""
        self.__do_test(SOURCE2, GOODTYPES2, BADTYPES2)

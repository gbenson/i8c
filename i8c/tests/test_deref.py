from i8c.tests import TestCase
from i8c.compiler import ParserError, ParsedError, StackTypeError

SOURCE = """\
typedef ptr ptr_alias

define test::deref
    argument %s arg

    deref %s
"""

class TestDeref(TestCase):
    TYPES = ("ptr", "ptr_alias",
             "int", "bool",
             "opaque", "func ()", "func int (ptr)",
             "u8", "u16", "u32", "u64",
             "s8", "s16", "s32", "s64")

    def test_deref(self):
        """Check that deref works."""
        for argtype in self.TYPES:
            argtype_is_ok = argtype.startswith("ptr")
            for rettype in self.TYPES:
                rettype_is_func = rettype.startswith("func")
                rettype_is_ok = not (rettype_is_func or rettype == "opaque")
                rettype_is_sized = rettype[0] in "su"
                expect_sign_extension = rettype in ("s8", "s16", "s32")

                source = SOURCE % (argtype, rettype)

                if rettype_is_func:
                    exception = ParserError
                elif not rettype_is_ok:
                    exception = ParsedError
                elif not argtype_is_ok:
                    exception = StackTypeError
                else:
                    exception = None

                if exception is not None:
                    self.assertRaises(exception, self.compile, source)
                    continue

                if not rettype_is_sized:
                    expect_ops = ["deref"]
                else:
                    expect_ops = ["deref_size"]

                if expect_sign_extension:
                    expect_ops.extend(("const1u", "dup", "dup",
                                       "shl", "swap", "shr"))
                    if rettype != "s32":
                        expect_ops.append("plus_uconst")
                    expect_ops.extend(("dup", "rot", "shl", "swap", "shra"))

                tree, output = self.compile(source)
                self.assertEqual(expect_ops, output.opnames)

from i8c.tests import TestCase
from i8c.runtime import NoteError
from i8c.runtime import types

class TestTypeMixin(object):
    def __eq__(self, other):
        return isinstance(self, type(other))

    def __ne__(self, other):
        raise NotImplementedError

I, P, O, F = (types.IntegerType, types.PointerType,
              types.OpaqueType, types.FunctionType)

GOODENC = (("", []),
           ("i", [I]),
           ("p", [P]),
           ("o", [O]),
           ("iipiop", [I, I, P, I, O, P]),
           ("F()", [F([], [])]),
           ("Fi()", [F([], [I])]),
           ("F(p)", [F([P], [])]),
           ("Fo(op)", [F([O, P], [O])]),
           ("Fo(io)i", [F([I, O], [O]), I]),
           ("ooFo(io)ip", [O, O, F([I, O], [O]), I, P]),
           ("FioFpo(ii)(op)i",
            [F([O, P],
               [I, O, F([I, I],
                        [P, O])]),
             I]),
           ("poFioFpo(ii)p(oFi(o)p)i",
            [P, O, F(
                [O, F([O],
                      [I]), P],
                [I, O, F([I, I],
                         [P, O]), P]), I]),
           )

BADENC = (
    # Types only valid for externals
    "f", "x",

    # Uppercase versions of valid types
    "P", "I", "O",

    # Undefined types
    "q", "%",

    # Various bad function encodings
    "F",
    "F(",
    "Fii(pp",
    "F)",
    "Fp)i(op)",
    )

class FakeSlice(object):
    filename = "<testcase>"
    start = 0

    def __init__(self, bytes):
        self.bytes = bytes

    def __len__(self):
        return len(self.bytes)

    def __getitem__(self, key):
        return self.bytes[key]

class TestRuntimeTypes(TestCase):
    def test_good_encodings(self):
        """Check that the runtime can decode lists of types."""
        for encoded, expect in GOODENC:
            decoded = types.decode(FakeSlice(encoded))
            self.assertEqual(decoded, expect)
            self.assertEqual(types.encode(decoded), encoded)

    def test_bad_encodings(self):
        """Check that the runtime rejects bad encoded types lists."""
        for encoded in BADENC:
            self.assertRaises(NoteError, types.decode, FakeSlice(encoded))

# -*- coding: utf-8 -*-
from . import CorruptNoteError, UnhandledNoteError

class Type(object):
    @classmethod
    def initialize(cls):
        cls.types = {}
        for item in globals().values():
            code = getattr(item, "code", None)
            if code is not None:
                assert not cls.types.has_key(code)
                cls.types[code] = item

class BasicType(Type):
    def __init__(self):
        raise AssertionError

    @classmethod
    def pack(cls):
        return cls.code

    @classmethod
    def unpack(cls, input, start):
        return start + 1

class IntPtrType(BasicType):
    name = "intptr"

class IntegerType(IntPtrType):
    code = "i"

class PointerType(IntPtrType):
    code = "p"

class OpaqueType(BasicType):
    code = "o"
    name = "opaque"

class FunctionType(Type):
    code = "F"
    name = "function"

    def __init__(self, ptypes=None, rtypes=None):
        assert (ptypes is None) == (rtypes is None)
        self.ptypes = ptypes
        self.rtypes = rtypes

    def __eq__(self, other):
        return not (self != other)

    def __ne__(self, other):
        assert self.ptypes is not None
        assert self.rtypes is not None
        assert other.ptypes is not None
        assert other.rtypes is not None
        return self.ptypes != other.ptypes or self.rtypes != other.rtypes

    def pack(self):
        return "%s%s(%s)" % (
            self.code, encode(self.rtypes), encode(self.ptypes))

    def unpack(self, input, start):
        assert self.ptypes is None and self.rtypes is None
        start, self.rtypes = decode(input, start + 1, "(")
        start, self.ptypes = decode(input, start + 1, ")")
        return start + 1

Type.initialize()

def decode(input, start=0, stop=None):
    result = []
    while start < len(input):
        code = input[start]
        if code == stop:
            return start, result
        thetype = Type.types.get(code, None)
        if thetype is None:
            raise UnhandledNoteError(input)
        if code.isupper():
            thetype = thetype()
        start = thetype.unpack(input, start)
        result.append(thetype)
    if stop is not None:
        raise CorruptNoteError(input)
    return result

def encode(list):
    return "".join([type.pack() for type in list])

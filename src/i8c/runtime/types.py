# -*- coding: utf-8 -*-
# Copyright (C) 2015-16 Red Hat, Inc.
# This file is part of the Infinity Note Execution Environment.
#
# The Infinity Note Execution Environment is free software; you can
# redistribute it and/or modify it under the terms of the GNU Lesser
# General Public License as published by the Free Software Foundation;
# either version 2.1 of the License, or (at your option) any later
# version.
#
# The Infinity Note Execution Environment is distributed in the hope
# that it will be useful, but WITHOUT ANY WARRANTY; without even the
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with the Infinity Note Execution Environment; if not,
# see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from .. import constants
from . import CorruptNoteError, UnhandledNoteError

class Type(object):
    @classmethod
    def initialize(cls):
        cls.types = {}
        for item in globals().values():
            code = getattr(item, "code", None)
            if code is not None:
                assert code not in cls.types
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
    code = constants.I8_TYPE_INT

class PointerType(IntPtrType):
    code = constants.I8_TYPE_PTR

class OpaqueType(BasicType):
    code = constants.I8_TYPE_OPAQUE
    name = "opaque"

class FunctionType(Type):
    code = constants.I8_TYPE_FUNC
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
        if thetype is FunctionType:
            thetype = thetype()
        start = thetype.unpack(input, start)
        result.append(thetype)
    if stop is not None:
        raise CorruptNoteError(input)
    return result

def encode(list):
    return "".join([type.pack() for type in list])

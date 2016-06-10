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

from ..compat import fprint, integer
from . import functions
from . import memory
from . import types
import ctypes
import sys

# XXX most every assert here should be a proper error

class Stack(object):
    def __init__(self, wordsize):
        self.__sint_t = getattr(ctypes, "c_int%d" % wordsize)
        self.__uint_t = getattr(ctypes, "c_uint%d" % wordsize)
        self.slots = []

    # Generic push and pop

    def pop_multi_onto(self, types, other):
        """Transfer values from one stack to another."""
        types = list(types)
        other.push_multi(types, self.pop_multi(types))

    def push_multi(self, types, values):
        types, values = map(list, (types, values))
        assert len(types) == len(values)
        typedvalues = list(zip(types, values))
        typedvalues.reverse()
        for type, value in typedvalues:
            self.push_typed(type, value)

    def pop_multi(self, types):
        result = []
        for type in types:
            result.append(self.pop_typed(type))
        return result

    def push_typed(self, type, value):
        assert type is not None
        self.push_boxed(self.__box(type, value))

    def pop_typed(self, type):
        assert type is not None
        return self.__unbox(type, self.pop_boxed())

    def push_boxed(self, boxed_value):
        assert not isinstance(boxed_value, integer)
        self.slots.insert(0, boxed_value)

    def pop_boxed(self):
        return self.slots.pop(0)

    # Push and pop shortcuts

    def push_intptr(self, value):
        self.push_typed(types.IntPtrType, value)

    def pop_unsigned(self):
        return self.pop_typed(types.IntPtrType)

    def pop_signed(self):
        return self.__sint_t(self.pop_unsigned()).value

    def pop_function(self):
        return self.__unbox_FUNCTION(None, self.pop_boxed())

    # Boxing and unboxing

    def __box(self, type, value):
        return getattr(
            self, "_Stack__box_" + type.name.upper())(type, value)

    def __unbox(self, type, value):
        return getattr(
            self, "_Stack__unbox_" + type.name.upper())(type, value)

    def __box_INTPTR(self, type, value):
        if isinstance(value, memory.Block):
            value = value.location
        assert isinstance(value, integer)
        return self.__uint_t(value)

    def __unbox_INTPTR(self, type, boxed):
        assert isinstance(boxed, self.__uint_t)
        return boxed.value

    def __box_FUNCTION(self, type, value):
        if not isinstance(value, functions.Function):
            assert callable(value)
            # Wrap anonymous functions provided by the testcase in
            # argument lists.  This is persistent (unboxing won't
            # remove it) so what you pop in this case is not exactly
            # what you pushed.
            value = functions.BuiltinFunction(AnonFuncRef(type), value)
        assert value.type == type
        return value

    def __unbox_FUNCTION(self, type, boxed):
        assert isinstance(boxed, functions.Function)
        assert type is None or boxed.type == type
        return boxed

    def __box_OPAQUE(self, type, value):
        return Opaque(value)

    def __unbox_OPAQUE(self, type, boxed):
        assert isinstance(boxed, Opaque)
        return boxed.value

    # Tracing

    def trace(self, tracelevel):
        depth = tracelevel + 1
        for item, index in zip(self.slots[:depth], range(depth)):
            if isinstance(item, self.__uint_t):
                value = item.value
                item = "%d" % value
                if value < 0 or value > 15:
                    item += " (0x%x)" % value
            fprint(sys.stdout, "    stack[%d] = %s" % (index, item))
        fprint(sys.stdout)

class AnonFuncRef(object):
    def __init__(self, type):
        self.provider = "i8x"
        self.name = "anonymous_function_%x" % id(self)
        self.ptypes = type.ptypes
        self.rtypes = type.rtypes

class Opaque(object):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "OPAQUE [0x%x]" % id(self)

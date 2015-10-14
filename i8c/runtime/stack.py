# -*- coding: utf-8 -*-
from . import functions
import ctypes
import types

# XXX most every assert here should be a proper error

class Stack(object):
    def __init__(self, wordsize):
        self.__sint_t = getattr(ctypes, "c_int%d" % wordsize)
        self.__uint_t = getattr(ctypes, "c_uint%d" % wordsize)
        self.slots = []

    # Generic push and pop

    def pop_multi_onto(self, types, other):
        """Transfer values from one stack to another."""
        other.push_multi(types, self.pop_multi(types))

    def push_multi(self, types, values):
        assert len(types) == len(values)
        typedvalues = zip(types, values)
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
        assert not isinstance(boxed_value, (int, long))
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
        assert isinstance(value, (int, long))
        return self.__uint_t(value)

    def __unbox_INTPTR(self, type, boxed):
        assert isinstance(boxed, self.__uint_t)
        return boxed.value

    def __box_FUNCTION(self, type, value):
        assert isinstance(value, functions.Function)
        assert value.type == type
        return value

    def __unbox_FUNCTION(self, type, boxed):
        assert isinstance(boxed, functions.Function)
        assert type is None or boxed.type == type
        return boxed

    # Tracing

    def trace(self, tracelevel):
        depth = tracelevel + 1
        for item, index in zip(self.slots[:depth], range(depth)):
            if isinstance(item, self.__uint_t):
                value = item.value
                item = "%d" % value
                if value < 0 or value > 15:
                    item += " (0x%x)" % value
            print "    stack[%d] = %s" % (index, item)
        print

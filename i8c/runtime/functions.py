# -*- coding: utf-8 -*-
# Copyright (C) 2015 Red Hat, Inc.
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

from .. import constants
from . import *
from . import operations
from . import types
import struct

class Function(object):
    def __init__(self, src):
        self.src = src
        self.__sig_set = False

    @property
    def byteorder(self):
        return self.src.byteorder

    def set_signature(self, provider, name, ptypes, rtypes):
        assert not self.__sig_set
        self.provider = provider
        self.name = name
        self.ptypes = ptypes
        self.rtypes = rtypes
        self.type = types.FunctionType(ptypes, rtypes)
        self.__sig_set = True

    @property
    def signature(self):
        return "%s::%s(%s)%s" % (self.provider, self.name,
                                 types.encode(self.ptypes),
                                 types.encode(self.rtypes))

    def __str__(self):
        return self.signature

class BuiltinFunction(Function):
    """A function provided by the note consumer."""

    def __init__(self, ref, impl):
        Function.__init__(self, ref)
        self.set_signature(ref.provider, ref.name, ref.ptypes, ref.rtypes)
        self.impl = impl

    def execute(self, ctx, stack):
        args = stack.pop_multi(self.ptypes)
        args.reverse()
        result = self.impl(*args)
        if len(self.rtypes) == 0:
            assert result is None
            result = []
        elif len(self.rtypes) == 1:
            result = [result]
        stack.push_multi(self.rtypes, result)

class BytecodeFunction(Function):
    def __init__(self, src):
        Function.__init__(self, src)

        # Parse the header
        hdrformat = self.byteorder + "11H"
        expect_hdrsize = struct.calcsize(hdrformat)
        (magic, version, hdrsize, codesize, externsize, provider_o,
         name_o, ptypes_o, rtypes_o, etypes_o, self.max_stack) \
            = struct.unpack(hdrformat, src[:expect_hdrsize].bytes)

        # Check the header
        if magic != constants.I8_FUNCTION_MAGIC:
            if magic >> 8 == magic & 0xFF:
                raise CorruptNoteError(self.src)
            else:
                raise UnhandledNoteError(self.src)
        if version != 1:
            raise UnhandledNoteError(self.src + 2)
        if hdrsize != expect_hdrsize - 4:
            raise CorruptNoteError(self.src + 4)

        # Work out where everything is
        codestart = 4 + hdrsize
        codelimit = codestart + codesize
        self.code = self.src[codestart:codelimit]

        externstart = codelimit
        externlimit = externstart + externsize
        externs = self.src[externstart:externlimit]

        stringstart = externlimit
        self.__strings = src[stringstart:]

        # Extract the header's strings
        provider, name, ptypes, rtypes, etypes \
            = map(self.get_string,
                  (provider_o, name_o,
                   ptypes_o, rtypes_o, etypes_o))

        # Set our signature
        ptypes = types.decode(ptypes)
        rtypes = types.decode(rtypes)
        self.set_signature(provider.bytes, name.bytes, ptypes, rtypes)

        # Load the bytecode and externals
        self.__load_bytecode()
        self.__load_externals(externs, etypes)

    def get_string(self, start):
        unterminated = self.__strings + start
        limit = unterminated.bytes.find("\0")
        if limit < 0:
            raise CorruptNoteError(unterminated)
        return unterminated[:limit]

    def __load_bytecode(self):
        self.ops = {}
        pc, limit = 0, len(self.code)
        while pc < limit:
            op = operations.Operation(self, pc)
            self.ops[pc] = op
            pc += op.size
        if pc != limit:
            raise CorruptNoteError(self.code + pc)

    def __load_externals(self, table, types):
        self.externals = []
        num_slots = len(types)
        if num_slots == 0:
            return
        slotsize, check = divmod(len(table), num_slots)
        if check != 0:
            raise CorruptNoteError(types)
        for index in range(num_slots):
            klass = {"f": UnresolvedFunction,
                     "x": UnrelocatedAddress}.get(types[index], None)
            if klass is None:
                raise UnhandledNoteError(self)
            start = index * slotsize
            limit = start + slotsize
            self.externals.append(klass(self, table[start:limit]))

    @property
    def external_functions(self):
        return [str(ext)
                for ext in self.externals
                if isinstance(ext, UnresolvedFunction)]

    @property
    def external_pointers(self):
        return [ext.value
                for ext in self.externals
                if isinstance(ext, UnrelocatedAddress)]

    def execute(self, ctx, caller_stack):
        stack = ctx.new_stack()
        caller_stack.pop_multi_onto(self.ptypes, stack)
        for external in self.externals:
            stack.push_typed(*external.resolve(ctx))
        pc, return_pc = 0, len(self.code)
        while pc >= 0 and pc < return_pc:
            op = self.ops.get(pc, None)
            if op is None:
                raise BadJumpError(stack.op)
            stack.op = op
            pc_adjust = op.execute(ctx, stack)
            pc += op.size
            if pc_adjust is not None:
                pc += pc_adjust
            last_op = op
        if pc != return_pc:
            raise BadJumpError(stack.op)
        ctx.trace_return((self.signature, pc), stack)
        stack.pop_multi_onto(self.rtypes, caller_stack)

class UnresolvedFunction(Function):
    def __init__(self, referrer, slot):
        Function.__init__(self, slot)
        self.referrer = referrer
        format = slot.byteorder + "4H"
        slotsize = struct.calcsize(format)
        provider, name, ptypes, rtypes \
            = map(referrer.get_string,
                  struct.unpack(format, slot[:slotsize].bytes))
        ptypes = types.decode(ptypes)
        rtypes = types.decode(rtypes)
        self.set_signature(provider.bytes, name.bytes, ptypes, rtypes)

    def resolve(self, ctx):
        return self.type, ctx.get_function(self)

class UnrelocatedAddress(object):
    def __init__(self, referrer, slot):
        format = {4: "I", 8: "Q"}.get(len(slot), None)
        if format is None:
            raise UnhandledNoteError(slot)
        format = slot.byteorder + format
        self.value = struct.unpack(format, slot.bytes)[0]

    def resolve(self, ctx):
        return types.PointerType, self.value

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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from .. import constants
from . import *
from . import leb128
from . import operations
from . import types
import copy
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
    CHUNKNAMES = {}
    for name in dir(constants):
        if name.startswith("I8_CHUNK_"):
            value = getattr(constants, name)
            assert not value in CHUNKNAMES
            CHUNKNAMES[value] = name
    del name, value

    def __init__(self, src):
        Function.__init__(self, src)
        self.__split_chunks()
        self.__unpack_info()
        self.__unpack_code()
        self.__unpack_etab()

    def __split_chunks(self):
        offset = 0
        while offset < len(self.src):
            start = offset
            offset, type = leb128.read_uleb128(self.src, offset)
            offset, version = leb128.read_uleb128(self.src, offset)
            offset, size = leb128.read_uleb128(self.src, offset)
            limit = offset + size
            name = self.CHUNKNAMES.get(type, None)
            if name is not None:
                assert name.startswith("I8_CHUNK_")
                name = name[9:].lower()
                if hasattr(self, name):
                    raise CorruptNoteError(self.src + start)
                chunk = self.src[offset:limit]
                chunk.version = version
                setattr(self, name, chunk)
            offset = limit
        if offset != len(self.src):
            raise CorruptNoteError(self.src)

    def get_string(self, start):
        if not hasattr(self, "stab"):
            raise UnhandledNoteError(self.src)
        if self.stab.version != 1:
            raise UnhandledNoteError(self.stab)
        unterminated = self.stab + start
        limit = unterminated.bytes.find(b"\0")
        if limit < 0:
            raise CorruptNoteError(unterminated)
        return unterminated[:limit]

    def __unpack_info(self):
        if not hasattr(self, "info"):
            raise UnhandledNoteError(self.src)
        if self.info.version != 1:
            raise UnhandledNoteError(self.info)
        offset, provider_o = leb128.read_uleb128(self.info, 0)
        offset, name_o = leb128.read_uleb128(self.info, offset)
        offset, ptypes_o = leb128.read_uleb128(self.info, offset)
        offset, rtypes_o = leb128.read_uleb128(self.info, offset)
        offset, self.max_stack = leb128.read_uleb128(self.info, offset)

        provider, name, ptypes, rtypes \
            = map(self.get_string,
                  (provider_o, name_o, ptypes_o, rtypes_o))

        ptypes = types.decode(ptypes)
        rtypes = types.decode(rtypes)
        self.set_signature(provider.text, name.text, ptypes, rtypes)

    def __unpack_code(self):
        self.ops = {}
        if not hasattr(self, "code"):
            return
        if self.code.version != 1:
            raise UnhandledNoteError(self.code)

        bomfmt = self.byteorder + b"H"
        bomsize = struct.calcsize(bomfmt)
        byteorder = struct.unpack(bomfmt, self.code[:bomsize].bytes)[0]
        if byteorder != constants.I8_BYTE_ORDER_MARK:
            raise UnhandledNoteError(self.code)
        self.code += bomsize

        pc, limit = 0, len(self.code)
        while pc < limit:
            op = operations.Operation(self, pc)
            self.ops[pc] = op
            pc += op.size
        if pc != limit:
            raise CorruptNoteError(self.code + pc)

    def __unpack_etab(self):
        self.externals = []
        if not hasattr(self, "etab"):
            return
        if self.etab.version != 1:
            raise UnhandledNoteError(self.etab)
        unterminated = copy.copy(self.etab)
        while len(unterminated):
            offset, type = leb128.read_uleb128(unterminated, 0)
            klass = {constants.I8_TYPE_RAWFUNC: UnresolvedFunction,
                     constants.I8_TYPE_RELADDR: UnrelocatedAddress}.get(
                chr(type), None)
            if klass is None:
                raise UnhandledNoteError(unterminated)
            unterminated += offset
            extern = klass(self, unterminated)
            self.externals.append(extern)
            unterminated += len(extern.src)

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
    def __init__(self, referrer, unterminated):
        offset, provider_o = leb128.read_uleb128(unterminated, 0)
        offset, name_o = leb128.read_uleb128(unterminated, offset)
        offset, ptypes_o = leb128.read_uleb128(unterminated, offset)
        offset, rtypes_o = leb128.read_uleb128(unterminated, offset)
        Function.__init__(self, unterminated[:offset])

        provider, name, ptypes, rtypes \
            = map(referrer.get_string,
                  (provider_o, name_o, ptypes_o, rtypes_o))

        ptypes = types.decode(ptypes)
        rtypes = types.decode(rtypes)
        self.set_signature(provider.text, name.text, ptypes, rtypes)

    def resolve(self, ctx):
        return self.type, ctx.get_function(self)

class UnrelocatedAddress(object):
    def __init__(self, referrer, unterminated):
        offset, self.value = leb128.read_uleb128(unterminated, 0)
        self.src = unterminated[:offset]

    def resolve(self, ctx):
        return types.PointerType, self.value

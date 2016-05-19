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

from ..compat import integer
from .. import archspec
from .. import constants
from . import *
from . import leb128
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
        args = stack.pop_multi(reversed(self.ptypes))
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
        self.__split_chunks()
        self.__unpack_signature()
        self.__unpack_codeinfo()
        self.__unpack_bytecode()
        self.__unpack_externals()

    def __split_chunks(self):
        self.chunks, offset = {}, 0
        while offset < len(self.src):
            start = offset
            offset, type_id = leb128.read_uleb128(self.src, offset)
            offset, version = leb128.read_uleb128(self.src, offset)
            offset, size = leb128.read_uleb128(self.src, offset)
            limit = offset + size
            if type_id not in self.chunks:
                self.chunks[type_id] = []
            chunk = self.src[offset:limit]
            chunk.version = version
            self.chunks[type_id].append(chunk)
            offset = limit
        if offset != len(self.src):
            raise CorruptNoteError(self.src)

    def one_chunk(self, type_id, supported_versions, is_mandatory):
        if isinstance(supported_versions, integer):
            supported_versions = (supported_versions,)
        chunks = self.chunks.get(type_id, None)
        if chunks is None:
            if not is_mandatory:
                return
            raise UnhandledNoteError(self.src)
        if len(chunks) != 1:
            # The second chunk is the first error
            raise UnhandledNoteError(chunks[1])
        chunk = chunks[0]
        if chunk.version not in supported_versions:
            raise UnhandledNoteError(chunk)
        return chunk

    def get_string(self, start):
        chunk = self.one_chunk(constants.I8_CHUNK_STRINGS, 1, True)
        unterminated = chunk + start
        limit = unterminated.bytes.find(b"\0")
        if limit < 0:
            raise CorruptNoteError(unterminated)
        return unterminated[:limit]

    def __unpack_signature(self):
        chunk = self.one_chunk(constants.I8_CHUNK_SIGNATURE, 2, True)

        offset, provider_o = leb128.read_uleb128(chunk, 0)
        offset, name_o = leb128.read_uleb128(chunk, offset)
        offset, ptypes_o = leb128.read_uleb128(chunk, offset)
        offset, rtypes_o = leb128.read_uleb128(chunk, offset)

        provider, name, ptypes, rtypes \
            = map(self.get_string,
                  (provider_o, name_o, ptypes_o, rtypes_o))

        ptypes = types.decode(ptypes)
        rtypes = types.decode(rtypes)
        self.set_signature(provider.text, name.text, ptypes, rtypes)

    def __unpack_codeinfo(self):
        chunk = self.one_chunk(constants.I8_CHUNK_CODEINFO, 1, False)
        if chunk is None:
            return

        expect = archspec.encode(chunk.wordsize)
        format = self.byteorder + b"H"
        offset = struct.calcsize(format)
        actual = struct.unpack(format, chunk[:offset].bytes)[0]
        if actual != expect:
            raise UnhandledNoteError(chunk)

        offset, self.max_stack = leb128.read_uleb128(chunk, offset)

    def __unpack_bytecode(self):
        self.ops = {}

        chunk = self.one_chunk(constants.I8_CHUNK_BYTECODE, 3, False)
        if chunk is None:
            return

        self.bytecode = chunk
        pc, limit = 0, len(self.bytecode)
        while pc < limit:
            op = operations.Operation(self, pc)
            self.ops[pc] = op
            pc += op.size
        if pc != limit:
            raise CorruptNoteError(self.bytecode + pc)

    def __unpack_externals(self):
        self.externals = []

        chunk = self.one_chunk(constants.I8_CHUNK_EXTERNALS, 2, False)
        if chunk is None:
            return

        unterminated = chunk
        while len(unterminated):
            extern = UnresolvedFunction(self, unterminated)
            self.externals.append(extern)
            unterminated += len(extern.src)

    @property
    def external_functions(self):
        return [str(ext)
                for ext in self.externals
                if isinstance(ext, UnresolvedFunction)]

    def execute(self, ctx, caller_stack):
        stack = ctx.new_stack()
        caller_stack.pop_multi_onto(reversed(self.ptypes), stack)
        pc, return_pc = 0, len(self.bytecode)
        while pc >= 0 and pc < return_pc:
            op = self.ops.get(pc, None)
            if op is None:
                raise BadJumpError(stack.op)
            stack.op = op
            pc_adjust = op.execute(ctx, self.externals, stack)
            pc += op.size
            if pc_adjust is not None:
                pc += pc_adjust
            last_op = op
        if pc != return_pc:
            raise BadJumpError(stack.op)
        ctx.trace_return((self.signature, pc), stack)
        stack.pop_multi_onto(self.rtypes, caller_stack)

    @property
    def coverage(self):
        ops_hit = opcount = 0
        for op in self.ops.values():
            if op.hitcount > 0:
                ops_hit += 1
            opcount += 1
        return ops_hit, opcount

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

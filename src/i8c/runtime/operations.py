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
from . import BadDerefError
from . import UnhandledNoteError
from . import leb128
import operator
import struct

class Operation(object):
    NAMES = {}
    for name in dir(constants):
        if name[2:6] == "_OP_":
            assert name not in NAMES
            NAMES[getattr(constants, name)] = name
    del name

    OPERANDS = {
        constants.DW_OP_addr: ["address"],
        constants.DW_OP_const1u: ["u1"],
        constants.DW_OP_const1s: ["s1"],
        constants.DW_OP_const2u: ["u2"],
        constants.DW_OP_const2s: ["s2"],
        constants.DW_OP_const4u: ["u4"],
        constants.DW_OP_const4s: ["s4"],
        constants.DW_OP_const8u: ["u8"],
        constants.DW_OP_const8s: ["s8"],
        constants.DW_OP_constu: ["uleb128"],
        constants.DW_OP_consts: ["sleb128"],
        constants.DW_OP_pick: ["u1"],
        constants.DW_OP_plus_uconst: ["uleb128"],
        constants.DW_OP_bra: ["s2"],
        constants.DW_OP_skip: ["s2"],
        constants.DW_OP_breg0: ["sleb128"],
        constants.DW_OP_breg1: ["sleb128"],
        constants.DW_OP_breg2: ["sleb128"],
        constants.DW_OP_breg3: ["sleb128"],
        constants.DW_OP_breg4: ["sleb128"],
        constants.DW_OP_breg5: ["sleb128"],
        constants.DW_OP_breg6: ["sleb128"],
        constants.DW_OP_breg7: ["sleb128"],
        constants.DW_OP_breg8: ["sleb128"],
        constants.DW_OP_breg9: ["sleb128"],
        constants.DW_OP_breg10: ["sleb128"],
        constants.DW_OP_breg11: ["sleb128"],
        constants.DW_OP_breg12: ["sleb128"],
        constants.DW_OP_breg13: ["sleb128"],
        constants.DW_OP_breg14: ["sleb128"],
        constants.DW_OP_breg15: ["sleb128"],
        constants.DW_OP_breg16: ["sleb128"],
        constants.DW_OP_breg17: ["sleb128"],
        constants.DW_OP_breg18: ["sleb128"],
        constants.DW_OP_breg19: ["sleb128"],
        constants.DW_OP_breg20: ["sleb128"],
        constants.DW_OP_breg21: ["sleb128"],
        constants.DW_OP_breg22: ["sleb128"],
        constants.DW_OP_breg23: ["sleb128"],
        constants.DW_OP_breg24: ["sleb128"],
        constants.DW_OP_breg25: ["sleb128"],
        constants.DW_OP_breg26: ["sleb128"],
        constants.DW_OP_breg27: ["sleb128"],
        constants.DW_OP_breg28: ["sleb128"],
        constants.DW_OP_breg29: ["sleb128"],
        constants.DW_OP_breg30: ["sleb128"],
        constants.DW_OP_breg31: ["sleb128"],
        constants.DW_OP_regx: ["uleb128"],
        constants.DW_OP_fbreg: ["sleb128"],
        constants.DW_OP_bregx: ["uleb128", "sleb128"],
        constants.DW_OP_piece: ["uleb128"],
        constants.DW_OP_deref_size: ["u1"],
        constants.DW_OP_xderef_size: ["u1"],
        constants.I8_OP_load_external: ["uleb128"],
        constants.I8_OP_deref_int: ["sleb128"],
        constants.I8_OP_cast_int2ptr: ["uleb128"],
        constants.I8_OP_cast_ptr2int: ["uleb128"],
        constants.I8_OP_warn: ["string"],
    }

    OPTABLE = {
        constants.DW_OP_abs: (abs, 1, True),
        constants.DW_OP_and: (operator.and_, 2, False),
        constants.DW_OP_div: (operator.floordiv, 2, True),
        constants.DW_OP_minus: (operator.sub, 2, False),
        constants.DW_OP_mod: (operator.mod, 2, False),
        constants.DW_OP_mul: (operator.mul, 2, False),
        constants.DW_OP_or: (operator.or_, 2, False),
        constants.DW_OP_neg: (operator.neg, 1, True),
        constants.DW_OP_not: (operator.invert, 1, False),
        constants.DW_OP_plus: (operator.add, 2, False),
        constants.DW_OP_shl: (operator.lshift, 2, False),
        constants.DW_OP_shr: (operator.rshift, 2, False),
        constants.DW_OP_shra: (operator.rshift, 2, True),
        constants.DW_OP_xor: (operator.xor, 2, False),
        constants.DW_OP_eq: (operator.eq, 2, True),
        constants.DW_OP_ge: (operator.ge, 2, True),
        constants.DW_OP_gt: (operator.gt, 2, True),
        constants.DW_OP_le: (operator.le, 2, True),
        constants.DW_OP_lt: (operator.lt, 2, True),
        constants.DW_OP_ne: (operator.ne, 2, True),
    }

    FIXEDSIZE = {}
    for code in "bBhHiIqQ":
        code = bytes(code.encode("utf-8"))
        size = struct.calcsize(code)
        type = "%s%d" % (code.isupper() and "u" or "s", size)
        assert type not in FIXEDSIZE
        FIXEDSIZE[type] = size, code
    del code, size, type

    def __init__(self, function, pc):
        src = function.bytecode + pc
        self.get_string = function.get_string
        # Read the opcode
        self.opcode = ord(src[0])
        next = src + 1
        if self.opcode == constants.DW_OP_GNU_wide_op:
            size, widecode = self.decode_uleb128(next)
            self.opcode = widecode + 0x100
            next += size
        if self.opcode not in self.NAMES:
            raise UnhandledNoteError(src)
        # Read the operands
        self.operands = []
        for type in self.OPERANDS.get(self.opcode, ()):
            sizecode = self.FIXEDSIZE.get(type, None)
            if sizecode is not None:
                size, fmt = sizecode
                fmt = src.byteorder + fmt
                value = struct.unpack(fmt, next[:size].bytes)[0]
            else:
                size, value = getattr(self, "decode_" + type)(next)
            self.operands.append(value)
            next += size
        # Store our source location for exceptions
        self.src = src[:next.start - src.start]
        # Store our location and encoded form for tracing
        self.location = (function, pc)
        self.encoded = self.src.text
        # Counter for coverage checks
        self.hitcount = 0
        # Tidy up
        del self.get_string

    @property
    def size(self):
        return len(self.src)

    @property
    def byteorder(self):
        return self.src.byteorder

    @property
    def function(self):
        return self.location[0]

    @staticmethod
    def decode_address(code):
        return code.wordsize >> 3, code.symbol_names

    @staticmethod
    def decode_uleb128(code):
        return leb128.read_uleb128(code, 0)

    @staticmethod
    def decode_sleb128(code):
        return leb128.read_sleb128(code, 0)

    def decode_string(self, code):
        size, index = self.decode_uleb128(code)
        return size, self.get_string(index).text

    @property
    def name(self):
        result = self.NAMES[self.opcode]
        assert result[2:6] == "_OP_"
        return result[6:]

    @property
    def operand(self):
        assert len(self.operands) == 1
        return self.operands[0]

    def __trace(self, ctx, stack):
        ctx.trace_operation(self.location, stack,
                            " ".join("%02x" % ord(c)
                                     for c in self.encoded),
                            " ".join([self.NAMES[self.opcode]]
                                     + list(map(repr, self.operands))))

    def execute(self, ctx, externals, stack):
        self.__trace(ctx, stack)
        self.hitcount += 1
        if (self.opcode >= constants.DW_OP_lit0
              and self.opcode <= constants.DW_OP_lit31):
            impl = self.__exec_litN
        elif (self.opcode >= constants.DW_OP_const1u
              and self.opcode <= constants.DW_OP_consts):
            impl = self.__exec_constX
        elif self.opcode in self.OPTABLE:
            impl = self.__exec_optable
        else:
            impl = getattr(self, "exec_" + self.name, None)
        if impl is None:
            raise NotImplementedError(self.name)
        return impl(ctx, externals, stack)

    def __exec_optable(self, ctx, externals, stack):
        func, num_args, is_signed = self.OPTABLE[self.opcode]
        pop = is_signed and stack.pop_signed or stack.pop_unsigned
        if num_args == 2:
            impl = self.__exec_binary
        else:
            assert num_args == 1
            impl = self.__exec_unary
        return impl(ctx, externals, stack, func, pop)

    def __exec_unary(self, ctx, externals, stack, func, pop):
        stack.push_intptr(func(pop()))

    def __exec_binary(self, ctx, externals, stack, func, pop):
        b = pop()
        a = pop()
        stack.push_intptr(func(a, b))

    def exec_addr(self, ctx, externals, stack):
        exception = None
        for name in self.operand:
            try:
                value = ctx.env.lookup_symbol(name)
            except KeyError as e:
                exception = e
                continue
            stack.push_intptr(value)
            return
        assert exception is not None
        raise exception

    def __exec_constX(self, ctx, externals, stack):
        stack.push_intptr(self.operand)

    def exec_bra(self, ctx, externals, stack):
        if stack.pop_unsigned() != 0:
            return self.operand

    def exec_deref(self, ctx, externals, stack):
        self.__exec_deref(ctx, externals, stack, 0)

    def exec_deref_int(self, ctx, externals, stack):
        assert self.operand != 0
        self.__exec_deref(ctx, externals, stack, self.operand)

    def __exec_deref(self, ctx, externals, stack, size):
        if size == 0:
            size = ctx.wordsize
        is_signed = size < 0
        if is_signed:
            size *= -1
        size >>= 3
        sizecode = "%s%d" % (is_signed and "s" or "u", size)
        sizecode = self.FIXEDSIZE.get(sizecode, None)
        if sizecode is None:
            raise UnhandledNoteError(self)
        check, fmt = sizecode
        assert check == size
        fmt = self.byteorder + fmt
        try:
            result = ctx.env.read_memory(fmt, stack.pop_unsigned())
        except KeyError as e:
            raise BadDerefError(self, ctx.env.memory, e.args[0])
        stack.push_intptr(struct.unpack(fmt, result)[0])

    def exec_cast_int2ptr(self, ctx, externals, stack):
        pass

    def exec_cast_ptr2int(self, ctx, externals, stack):
        pass

    def exec_drop(self, ctx, externals, stack):
        stack.pop_boxed()

    def exec_dup(self, ctx, externals, stack):
        stack.push_boxed(stack.slots[0])

    def exec_call(self, ctx, externals, stack):
        callee = stack.pop_function()
        ctx.trace_call(callee, stack)
        callee.execute(ctx, stack)

    def __exec_litN(self, ctx, externals, stack):
        stack.push_intptr(self.opcode - constants.DW_OP_lit0)

    def exec_load_external(self, ctx, externals, stack):
        if self.operand == 0:
            external = self.function.type, self.function
        else:
            external = externals[self.operand - 1].resolve(ctx)
        stack.push_typed(*external)

    def exec_over(self, ctx, externals, stack):
        stack.push_boxed(stack.slots[1])

    def exec_pick(self, ctx, externals, stack):
        stack.push_boxed(stack.slots[self.operand])

    def exec_plus_uconst(self, ctx, externals, stack):
        a = stack.pop_unsigned()
        stack.push_intptr(a + self.operand)

    def exec_rot(self, ctx, externals, stack):
        a = stack.pop_boxed()
        b = stack.pop_boxed()
        c = stack.pop_boxed()
        stack.push_boxed(a)
        stack.push_boxed(c)
        stack.push_boxed(b)

    def exec_skip(self, ctx, externals, stack):
        return self.operand

    def exec_swap(self, ctx, externals, stack):
        a = stack.pop_boxed()
        b = stack.pop_boxed()
        stack.push_boxed(a)
        stack.push_boxed(b)

    def exec_warn(self, ctx, externals, stack):
        ctx.env.warn_caller(self.operand)

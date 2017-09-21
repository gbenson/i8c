# -*- coding: utf-8 -*-
# Copyright (C) 2017 Red Hat, Inc.
# This file is part of the Infinity Note Compiler.
#
# The Infinity Note Compiler is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# The Infinity Note Compiler is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Infinity Note Compiler.  If not, see
# <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from tests import TestCase, multiplexed

SOURCE = """\
define test::trace_me returns int
  argument ptr addr
  extern func int, int (int) native_func
  deref int32_t
  call native_func
  dup
  blt 0, label
  add
  return
label:
  drop
  warn "it's negative"
"""

class TestTracing(TestCase):
    NEGVALUE = 0x87654321
    POSVALUE = 0x80000000 - (NEGVALUE & 0x7fffffff)

    @TestCase.provide("test::native_func(i)ii")
    def __native_func(self, arg):
        return arg, -self.to_signed(arg)

    def warn_caller(self, *args):
        self.assertEqual(args, ("test::trace_me(p)i", "it's negative"))

    def setUp(self):
        tree, self.output = self.compile(SOURCE)
        self.addCleanup(delattr, self, "output")

        for output in self.output.variants:
            output.trace = self.__log_trace
            output.logged_trace = []
        self.output.add_multiplexed_property("logged_trace")

        self.__setup_memory()

    @multiplexed
    def __setup_memory(self):
        with self.memory.builder() as mem:
            self.addr = mem.alloc("sym1")
            self.addr.store_u32(0, self.NEGVALUE)

    def __log_trace(self, msg):
        self.trace.append(msg)

    @property
    def trace(self):
        output = self.output
        if not hasattr(output, "logged_trace"):
            output = output.variant[self.variant_index]
        return output.logged_trace

    def tpop(self, expect_result=None):
        """Pop and parse a trace message."""
        self.assertGreater(len(self.trace), 0)
        result = self.trace.pop(0)

        if expect_result is not None:
            print("(%s)" % result)
            self.assertEqual(result, expect_result)
            return

        result = result.split()
        self.assertEqual(len(result), 6)

        signature = result.pop(0)
        self.assertEqual(signature, "test::trace_me(p)i")

        self.assertTrue(result[0].startswith("0x"))
        result[0] = int(result[0], 16) # pc

        stack_depth = result.pop(2)
        self.assertEqual(stack_depth[0], "[")
        self.assertEqual(stack_depth[-1], "]")
        stack_depth = int(stack_depth[1:-1])

        stack = []
        for slot in range(2):
            value = result.pop(2)
            if slot >= stack_depth:
                self.assertEqual(value, "-" * 10)
                continue
            self.assertTrue(value.startswith("0x"))
            stack.append(int(value, 16))
        result.append(stack_depth)
        result.append(stack)

        print(result)
        return result

    def __call_testfunc(self):
        result = self.output.call("test::trace_me(p)i", self.addr)
        self.assertEqual(result, [self.POSVALUE])

    def test_without_tracing(self):
        """Test with tracing disabled."""
        self.assertEqual(self.output.tracelevel, 0)
        self.__call_testfunc()
        self.assertEqual(self.trace, [])

    @multiplexed
    def test_tracing(self):
        """Test with tracing enabled."""
        self.output.tracelevel = 1
        self.__call_testfunc()
        print("\n".join(self.trace) + "\n")
        negvalue = self.to_unsigned(-self.POSVALUE)

        # deref
        start_pc, opname, stack_depth, stack = self.tpop()
        self.assertEqual(opname, (self.output.backend == "libi8x"
                                  and (self.output.byteorder
                                       == self.system_byteorder
                                       and "I8X_OP_deref_i32n"
                                       or "I8X_OP_deref_i32r")
                                  or "I8_OP_deref_int"))
        self.assertEqual(stack_depth, 1)
        self.assertEqual(stack, [self.addr.location])

        # load external
        pc, opname, stack_depth, stack = self.tpop()
        self.assertEqual(pc, start_pc + 3)
        self.assertEqual(opname, "I8_OP_load_external")
        self.assertEqual(stack_depth, 1)
        self.assertEqual(stack, [negvalue])

        # call
        pc, opname, stack_depth, stack = self.tpop()
        self.assertEqual(pc, start_pc + 6)
        self.assertEqual(opname, "I8_OP_call")
        self.assertEqual(stack_depth, 2)
        self.assertEqual(stack[1:], [negvalue])
        self.tpop("test::native_func(i)ii: native call")
        self.tpop("test::native_func(i)ii: native return")

        # dup
        pc, opname, stack_depth, stack = self.tpop()
        self.assertEqual(pc, start_pc + 8)
        self.assertEqual(opname, "DW_OP_dup")
        self.assertEqual(stack_depth, 2)
        self.assertEqual(stack, [negvalue, self.POSVALUE])

        # lit0
        pc, opname, stack_depth, stack = self.tpop()
        self.assertEqual(pc, start_pc + 9)
        self.assertEqual(opname, "DW_OP_lit0")
        self.assertEqual(stack_depth, 3)
        self.assertEqual(stack, [negvalue, negvalue])

        # lt
        pc, opname, stack_depth, stack = self.tpop()
        self.assertEqual(pc, start_pc + 10)
        self.assertEqual(opname, "DW_OP_lt")
        self.assertEqual(stack_depth, 4)
        self.assertEqual(stack, [0, negvalue])

        # bra
        pc, opname, stack_depth, stack = self.tpop()
        self.assertEqual(pc, start_pc + 11)
        self.assertEqual(opname, "DW_OP_bra")
        self.assertEqual(stack_depth, 3)
        self.assertEqual(stack, [1, negvalue])

        # drop
        pc, opname, stack_depth, stack = self.tpop()
        self.assertEqual(pc, start_pc + 18)
        self.assertEqual(opname, "DW_OP_drop")
        self.assertEqual(stack_depth, 2)
        self.assertEqual(stack, [negvalue, self.POSVALUE])

        # warn
        pc, opname, stack_depth, stack = self.tpop()
        self.assertEqual(pc, start_pc + 19)
        self.assertEqual(opname, "I8_OP_warn")
        self.assertEqual(stack_depth, 1)
        self.assertEqual(stack, [self.POSVALUE])

        # return
        pc, opname, stack_depth, stack = self.tpop()
        self.assertEqual(pc, start_pc + 22)
        self.assertEqual(opname,
                         {"libi8x": "I8X_OP_return",
                          "python": "[return]"}[self.output.backend])
        self.assertEqual(stack_depth, 1)
        self.assertEqual(stack, [self.POSVALUE])

        self.assertEqual(self.trace, [])

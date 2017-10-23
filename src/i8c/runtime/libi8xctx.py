# -*- coding: utf-8 -*-
# Copyright (C) 2017 Red Hat, Inc.
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

from ..compat import fprint, str
from . import *
from . import context
import libi8x
import re
import sys
import syslog
import weakref

class Context(context.AbstractContext):
    def translate_exceptions(func):
        """Decorator to translate libi8x exceptions into ours."""
        def _func(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except libi8x.UnhandledNoteError as e:
                raise UnhandledNoteError(e)
            except libi8x.I8XError as e: # pragma: no cover
                raise NotImplementedError("libi8x." + e.__class__.__name__)
        return _func

    @classmethod
    def _class_init(cls):
        """Probe libi8x for wordsize, component versions, and
        default logging priority."""
        x = libi8x.to_unsigned(-1)
        while x:
            cls.MAX_WORDSIZE += 1
            x >>= 1
        cls.__components = []
        cls.__log_pri = libi8x.Context(0, cls.__clinit_logger).log_priority
        if not cls.__components:
            libi8x.Context(syslog.LOG_DEBUG, cls.__clinit_logger)
        for index, component in enumerate(cls.__components):
            if component.startswith("libi8x "):
                cls.INTERPRETER = cls.__components.pop(index)
                break
        cls.INTERPRETER += " (%s)" % ", ".join(cls.__components)
        del cls.__components

    @classmethod
    def __clinit_logger(cls, pri, filename, linenumber, function, msg):
        """Logger for component versions probe."""
        PREFIX = "using "
        if pri == syslog.LOG_DEBUG and msg.startswith(PREFIX):
            cls.__components.insert(0, msg[len(PREFIX):].rstrip())

    def __init__(self, *args, **kwargs):
        super(Context, self).__init__(*args, **kwargs)

        # Enable extra checks if we're in the I8C testsuite.
        self.__extra_checks = hasattr(self.env, "__i8c_testcase__")
        if self.__extra_checks:
            self.__dbg_log = []

        self.__bytecode_consumers = None
        flags = libi8x.DBG_MEM | libi8x.LOG_TRACE
        self.__ctx = libi8x.Context(flags, self.__logger)
        self.__ctx.FUNCTION_CLASS = Function
        self.__ctx.RELOCATION_CLASS = Relocation

        self.__inf = self.__ctx.new_inferior()
        self.__inf.read_memory = self.__read_memory
        self.__inf.relocate_address = self.__relocate

        self.__xctx = self.__ctx.new_xctx()

    def finalize(self):
        """Release any resources held by this Context."""
        if self.__ctx is not None:
            for func in self.__ctx.functions:
                func.is_persistent = False
                del func
        self.__ctx = self.__inf = self.__xctx = None

        if not self.__extra_checks:
            return

        SENSES = {"created": 1, "released": -1}
        counts = {}
        for entry in self.__dbg_log:
            priority, filename, line, function, msg = entry
            if priority != syslog.LOG_DEBUG:
                continue
            msg = msg.rstrip().split()
            if not msg:
                continue
            sense = SENSES.get(msg.pop(), None)
            if sense is None:
                continue
            what = " ".join(msg)
            count = counts.get(what, 0) + sense
            if count == 0:
                counts.pop(what)
            else:
                counts[what] = count

        self.env.assertTrue(not counts,
                            "\n  ".join(["unreleased items:"]
                                        + [" " + item
                                           for item in sorted(counts)]))

    def __logger(self, priority, filename, linenumber, function, msg):
        """Logging function for libi8x messages."""

        # Store log messages if we're in the I8C testsuite.
        if self.__extra_checks:
            self.__dbg_log.append(
                (priority, filename, linenumber, function, msg))

        # Write message to stderr if requested.
        if priority <= self.__log_pri: # pragma: no cover
            # User requested this with I8X_LOG.
            sys.stderr.write("i8x: %s: %s" % (function, msg))

        # Funnel tracing messages to AbstractContext._trace.
        if (priority == libi8x.LOG_TRACE
              and function.find("validate") < 0):
            self.__trace(msg)

        # Funnel messages from I8_OP_warn to the testcase.
        if (priority == syslog.LOG_WARNING
              and function.startswith("i8x_xctx_call")
              and msg.endswith("\n")):
            self.env.warn_caller(*msg[:-1].split(": ", 1))

        # Funnel itable dump traces to the consumer.
        if (self.__bytecode_consumers is not None
              and priority == syslog.LOG_INFO
              and function == "i8x_code_dump_itable"):
            for bcc in self.__bytecode_consumers:
                bcc.consume(msg)

    def __trace(self, msg):
        """Funnel tracing messages to AbstractContext._trace.

        Tries to be very conservative, while at the same time
        trying very hard to actually do something.  Note this
        silently drops any exceptions when running outside of
        I8C's testsuite.
        """
        args, kwargs = [], {}
        try:
            self.__parse_trace(args, kwargs, msg)
        except: # pragma: no cover
            if self.__extra_checks:
                raise
        try:
            self._trace(*args, **kwargs)
        except: # pragma: no cover
            if self.__extra_checks:
                raise

    @staticmethod
    def __parse_trace(args, kwargs, msg):
        signature, msg = msg.rstrip().split(None, 1)
        is_special = signature.endswith(":")
        if is_special:
            signature = signature[:-1]
        args.append(signature)
        if is_special:
            kwargs["opname"] = msg
            return

        msg = msg.split()
        args.append(int(msg.pop(0), 16)) # pc
        args.append(msg.pop(0))          # opname

        stack = []
        stack_depth = int(msg.pop(0).strip("[]"))
        for slot in range(stack_depth):
            if not msg:
                break
            stack.append(int(msg.pop(0), 16))
        stack += [None] * (stack_depth - len(stack))
        args.append(stack)

    # Methods to populate the context with Infinity functions.

    @translate_exceptions
    def import_note(self, ns):
        """Import one note."""
        bcc_raw = UnpackedBytecodeConsumer("i8x_code_unpack_bytecode")
        bcc_cooked = UnpackedBytecodeConsumer("i8x_code_setup_dispatch")
        self.__bytecode_consumers = (bcc_raw, bcc_cooked)

        func = self.__ctx.import_bytecode(ns.data, ns.srcname,
                                          ns.srcoffset)

        # Store the unpacked bytecode.
        ops = bcc_raw.ops
        if ops:
            last_op = max(ops.keys())
            check = ops.pop(last_op)
            self.env.assertEqual(check.fullname, "I8X_OP_return")
        func.ops = ops
        func.coverage_ops = bcc_cooked.ops
        self.__bytecode_consumers = None

        # Store any relocations.
        for reloc in func.relocations:
            start = reloc.srcoffset - ns.srcoffset
            src = ns[start:start + 1]
            reloc.operation.operands = (src.symbol_names,)

        return func

    @translate_exceptions
    def override(self, function):
        """Register a function, overriding any existing versions."""
        func = self.__ctx.import_native(
            function.signature,
            lambda xctx, inf, func, *args: function.impl(*args))
        unbound = getattr(function, "unbound", None)
        if unbound is not None:
            func.bind_to(unbound)
        ref = func.ref
        if ref.is_resolved:
            return

        # The function already existed; we've added another with the
        # same name and caused the funcref to become unresolved.  We
        # walk the list and unregister the ones that aren't ours.
        kill_list = [func2
                     for func2 in self.__ctx.functions
                     if (func2 is not func and func2.ref is ref)]
        while kill_list:
            func = kill_list.pop()
            func.is_persistent = False
            func.unregister()
            if self.__extra_checks:
                check = weakref.ref(func)
            del func
            if self.__extra_checks:
                self.env.assertIsNone(check())

        self.env.assertTrue(ref.is_resolved)

    # Methods for Infinity function execution.

    @translate_exceptions
    def call(self, callee, *args):
        """Call the specified function with the specified arguments."""
        return list(self.__xctx.call(self.__process_value(callee),
                                     self.__inf,
                                     *map(self.__process_value, args)))

    def __process_value(self, value):
        """Convert a Python value into something libi8x can use.
        """
        # If it's already an i8x_funcref then we're done.
        if isinstance(value, libi8x.FunctionReference):
            return value

        # Ditto if it doesn't look like a function object.
        signature = getattr(value, "signature", None)
        if signature is None:
            return value

        # Is this a UserFunction?
        unbound = getattr(value, "unbound", None)
        if unbound is not None:
            value = unbound
        bound_to = [func
                    for func in self.__ctx.functions
                    if func.is_bound_to(value)]
        if len(bound_to) == 1:
            return bound_to[0].ref

        # Just a regular function then.
        return signature

    def __read_memory(self, inf, addr, len):
        """Memory reader function."""
        fmt = {1: b"B", 2: b"H", 4: b"I", 8: b"Q"}[len]
        return self.env.read_memory(fmt, addr)

    def __relocate(self, inf, reloc):
        """Address relocation function."""
        return self.lookup_symbol(reloc.operation.operand, reloc)

    # Methods to convert between signed and unsigned integers.

    def to_signed(self, value):
        """Interpret an integer from the interpreter as signed."""
        return libi8x.to_signed(value)

    def to_unsigned(self, value):
        """Convert a signed integer to the interpreter's representation."""
        return libi8x.to_unsigned(value)

    # Methods for the I8C testsuite.

    @property
    def _i8ctest_functions(self):
        return self.__ctx.functions

class Function(libi8x.Function):
    __libi8x_persistent__ = True

    def __init__(self, *args, **kwargs):
        super(Function, self).__init__(*args, **kwargs)
        self.__bound_to = None

    def bind_to(self, ref):
        """Associate this function with an external reference."""
        self.__bound_to = ref

    def is_bound_to(self, ref):
        """Is this function bound to the specified object?"""
        return self.__bound_to is ref

class Relocation(libi8x.Relocation):
    @property
    def operation(self):
        result = self.function.ops[self.srcoffset - 1]
        assert result.fullname == "DW_OP_addr"
        return result

Context._class_init()

class UnpackedBytecodeConsumer(object):
    """Grab the decoded bytecode from the trace messages."""

    def __init__(self, stage):
        self.__start_re = re.compile(r"^%s(\s.*)?:\n$" % stage)
        self.ops = {}
        self.__started = False
        self.__finished = False

    def consume(self, msg):
        if not self.__started:
            if self.__start_re.match(msg) is not None:
                self.__started = True
        elif not self.__finished:
            op = self.__consume_op(msg)
            if op.fullname == "I8X_OP_return":
                self.__finished = True

    def __consume_op(self, msg):
        msg = msg.strip()

        pc, msg = msg.split(": ", 1)
        pc = self.__str_to_int(pc)
        assert pc not in self.ops

        msg = msg.split("=> ", 1)
        op = msg.pop(0)
        if len(msg) == 1:
            [msg] = msg
        else:
            assert op == "I8X_OP_return"
            del msg
        operands = op.rstrip().split()
        fullname = operands.pop(0)
        if fullname == "I8_OP_warn":
            assert len(operands) == 1
            extras = msg.split(" / ", 1)
            if len(extras) == 2:
                operand = extras[1]
            else:
                operand = ""
            operands = (operand,)
        else:
            operands = tuple(map(self.__str_to_int, operands))

        op = Operation(fullname, operands)
        self.ops[pc] = op
        return op

    @staticmethod
    def __str_to_int(value):
        if value.startswith("0x"):
            return int(value, 16)
        else:
            return int(value)

class Operation(context.AbstractOperation):
    def __init__(self, fullname, operands):
        self.fullname = fullname
        self.operands = operands

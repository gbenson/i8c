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
import sys
import syslog

class Context(context.AbstractContext):
    INTERPRETER = "UNKNOWN"

    def translate_exceptions(func):
        """Decorator to translate libi8x exceptions into ours."""
        def _func(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except libi8x.UnhandledNoteError as e:
                raise UnhandledNoteError(FakeSlice(e))
            except libi8x.I8XError as e: # pragma: no cover
                raise NotImplementedError("libi8x." + e.__class__.__name__)
        return _func

    @classmethod
    def _class_init(cls):
        """Probe libi8x for component versions and log priority."""
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
        self.__imports = []
        super(Context, self).__init__(*args, **kwargs)

        # Enable extra checks if we're in the I8C testsuite.
        self.__extra_checks = hasattr(self.env, "__i8c_testcase__")
        if self.__extra_checks:
            self.__dbg_log = []

        self.__upbcc = None
        flags = libi8x.DBG_MEM | libi8x.LOG_TRACE
        self.__ctx = libi8x.Context(flags, self.__logger)

        self.__inf = self.__ctx.new_inferior()
        self.__inf.read_memory = self.__read_memory
        self.__inf.relocate_address = self.__relocate

        self.__xctx = self.__ctx.new_xctx()

    def finalize(self):
        """Release any resources held by this Context."""
        super(Context, self).finalize()
        for func in self.__imports:
            del func.symbols_at
            del func
        del self.__imports
        del self.__xctx, self.__inf, self.__ctx

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
        if counts:
            print("Unreleased items:")
            for item in sorted(counts):
                print(" ", item)
            raise AssertionError("unreleased items")

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
            self.env.warn_caller(msg[:-1].split(": ", 1)[1])

        # Funnel itable dump traces to the consumer.
        if (self.__upbcc is not None
              and priority == syslog.LOG_INFO
              and function == "i8x_code_dump_itable"):
            self.__upbcc.consume(msg)

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
        assert ns.start == 0 # or need to adjust srcoffset
        srcoffset = ns.note.offset

        self.__upbcc = UnpackedBytecodeConsumer()
        func = self.__ctx.import_bytecode(ns.bytes, ns.filename,
                                          srcoffset)

        # Retain a reference to func so we can add things to it.
        # Without this the capsule wrapper will be collected as
        # this method exits.
        self.__imports.append(func)

        # Store the unpacked bytecode.
        func.ops = self.__upbcc.ops
        self.__upbcc = None

        # Store any relocations.  Note that this creates
        # circular references that are cleared in __del__.
        func.symbols_at = {}
        for reloc in func.relocations:
            start = reloc.source_offset - srcoffset
            src = ns[start:start + 1]
            func.symbols_at[reloc] = src.symbol_names

    @translate_exceptions
    def override(self, function):
        """Register a function, overriding any existing versions."""
        func = self.__ctx.import_native(
            function.signature,
            lambda xctx, inf, func, *args: function.impl(*args))
        ref = func.ref
        if not ref.is_resolved:
            # The function already existed; we've added another with the
            # same name and caused the funcref to become unresolved.  We
            # walk the list and unregister the ones that aren't ours.
            kill_list = [func2
                         for func2 in self.__ctx.functions
                         if func2 is not func and func2.ref is ref]
            assert kill_list
            for func in kill_list:
                self.__ctx.unregister(func)
        return ref

    # Methods for Infinity function execution.

    @translate_exceptions
    def call(self, callee, *args):
        """Call the specified function with the specified arguments."""
        return list(self.__xctx.call(self.__process_value(callee),
                                     self.__inf,
                                     *map(self.__process_value, args)))

    def __process_value(self, maybe_func):
        """Convert a Python value into something libi8x can use."""
        handle = getattr(maybe_func, "_handle", None)
        if handle is not None:
            return handle
        else:
            return getattr(maybe_func, "signature", maybe_func)

    def __read_memory(self, inf, addr, len):
        """Memory reader function."""
        fmt = {1: b"B", 2: b"H", 4: b"I", 8: b"Q"}[len]
        return self.env.read_memory(fmt, addr)

    def __relocate(self, inf, reloc):
        """Address relocation function."""
        for name in reloc.function.symbols_at[reloc]:
            try:
                value = self.env.lookup_symbol(name)
            except KeyError as e:
                exception = e
                continue
            return value
        assert exception is not None
        raise exception

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

class FakeSlice(object):
    """libi8x.I8XError location, wrapped like a provider.NoteSlice."""

    def __init__(self, libi8x_exception):
        self.filename = libi8x_exception.srcname
        self.start = libi8x_exception.srcoffset

Context._class_init()

class UnpackedBytecodeConsumer(object):
    """Grab the decoded bytecode from the trace messages."""

    def __init__(self):
        self.ops = {}
        self.__started = False
        self.__finished = False

    def consume(self, msg):
        if not self.__started:
            if msg == "i8x_code_unpack_bytecode:\n":
                self.__started = True
        elif msg.find("I8X_OP_return") != -1:
            self.__finished = True
        elif not self.__finished:
            self.__consume_op(msg)

    def __consume_op(self, msg):
        msg = msg.strip()

        pc, msg = msg.split(": ", 1)
        pc = self.__str_to_int(pc)
        assert pc not in self.ops

        op, msg = msg.split("=> ", 1)
        operands = op.rstrip().split()
        fullname = operands.pop(0)
        operands = tuple(map(self.__str_to_int, operands))

        # XXX process the remainder?
        # It has next_pc values, and I8_OP_warn strings.

        self.ops[pc] = Operation(fullname, operands)

    @staticmethod
    def __str_to_int(value):
        if value.startswith("0x"):
            return int(value, 16)
        else:
            return int(value)

class Operation(object):
    def __init__(self, fullname, operands):
        self.fullname = fullname
        self.operands = operands

    @property
    def name(self):
        assert self.fullname[2:6] == "_OP_"
        return self.fullname[6:]

    @property
    def operand(self):
        assert len(self.operands) == 1
        return self.operands[0]

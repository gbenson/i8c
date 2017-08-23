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
from . import functions
from . import types
import _libi8x as py8x
import sys
import syslog

class Context(context.AbstractContext):
    INTERPRETER = "libi8x interpreter (experimental)"
    MAX_STACK = 512

    def __init__(self, *args, **kwargs):
        self.__imports = []
        super(Context, self).__init__(*args, **kwargs)

        self.__upbcc = None
        self.__ctx = py8x.ctx_new(PY8XObject.new,
                                  py8x.I8X_DBG_MEM,
                                  self.__logger)

        # Boost log priority if necessary so we can access warnings
        # and tracing messages.  Our logging function filters these
        # according to the priority the user originally requested.
        self.__log_pri = py8x.ctx_get_log_priority(self.__ctx)
        if self.__log_pri < py8x.I8X_LOG_TRACE:
            py8x.ctx_set_log_priority(self.__ctx, py8x.I8X_LOG_TRACE)

        self.__inf = py8x.inf_new(self.__ctx)
        py8x.inf_set_read_mem_fn(self.__inf, self.__read_memory)
        py8x.inf_set_relocate_fn(self.__inf, self.__relocate)

        self.__xctx = py8x.xctx_new(self.__ctx, self.MAX_STACK)

    def __del__(self):
        for func in self.__imports:
            del func.symbols_at
        del self.__imports

    def __logger(self, priority, filename, linenumber, function, msg):
        """Logging function for libi8x messages."""
        try:
            print_it = priority <= self.__log_pri
        except AttributeError: # pragma: no cover
            # We haven't touched the log priority yet, so this
            # is something the user requested with the I8X_LOG
            # environment variable.
            print_it = True

        if print_it: # pragma: no cover
            sys.stderr.write("i8x: %s: %s" % (function, msg))
        elif (self.tracelevel > 0
                and priority == syslog.LOG_DEBUG
                and (function.startswith("i8x_xctx_call")
                     or function.startswith("i8x_xctx_trace"))):
            # Let trace messages through if requested.
            sys.stderr.write(msg)

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

    # Methods to populate the context with Infinity functions.

    __exception_map = {
        "Unhandled note": UnhandledNoteError
        }

    def import_note(self, ns):
        """Import one note."""
        assert ns.start == 0 # or need to adjust srcoffset
        srcoffset = ns.note.offset

        self.__upbcc = UnpackedBytecodeConsumer()
        exception = None
        try:
            func = py8x.ctx_import_bytecode(self.__ctx, ns.bytes,
                                            ns.filename, srcoffset)
        except py8x.I8XError as e:
            sep = ": "
            msg = e.args[0].split(sep)
            cls = self.__exception_map.get(msg.pop(), None)
            if cls is None:
                exception = e
            else:
                exception = cls(sep.join(msg))
        if exception is not None:
            raise exception

        # Retain a reference to func so we can add things to it.
        # Without this the capsule wrapper will be collected as
        # this method exits.
        self.__imports.append(func)

        # Store the signature.
        funcref = py8x.func_get_funcref(func)
        func.signature = py8x.funcref_get_fullname(funcref)

        # Store the unpacked bytecode.
        func.ops = self.__upbcc.ops
        self.__upbcc = None

        # Store any relocations.  Note that this creates
        # circular references that are cleared in __del__.
        func.symbols_at = {}
        relocs = py8x.func_get_relocs(func)
        try:
            li = py8x.list_get_first(relocs)
            while True:
                reloc = py8x.listitem_get_object(li)
                start = py8x.reloc_get_src_offset(reloc) - srcoffset
                src = ns[start:start + 1]
                func.symbols_at[reloc] = src.symbol_names
                li = py8x.list_get_next(relocs, li)
        except StopIteration:
            pass

    def override(self, function):
        """Register a function, overriding any existing versions."""
        provider, name, ptypes, rtypes \
            = functions.unpack_signature(function.signature)
        func = py8x.ctx_import_native(self.__ctx,
                                      provider, name,
                                      types.encode(ptypes),
                                      types.encode(rtypes),
                                      self.__wrap_native_func(function.impl))

        ref = py8x.func_get_funcref(func)
        if py8x.funcref_is_resolved(ref):
            return

        # The function already existed; we've added another with the
        # same name and caused the funcref to become unresolved.  We
        # walk the list and unregister the ones that aren't ours.
        kill_list = []
        fnlist = py8x.ctx_get_functions(self.__ctx)
        try:
            li = py8x.list_get_first(fnlist)
            while True:
                func2 = py8x.listitem_get_object(li)
                if (func2 is not func
                    and py8x.func_get_funcref(func2) is ref):
                        kill_list.append(func2)
                li = py8x.list_get_next(fnlist, li)
        except StopIteration:
            pass

        assert kill_list
        for func in kill_list:
            py8x.ctx_unregister_func(self.__ctx, func)

    class __wrap_native_func(object):
        """Fix up native method return values for libi8x.

        libi8x expects all functions to return a sequence, but the
        original I8X interpreter allowed functions with only one
        return value to return the value by itself (i.e. not in a
        one-item sequence).  This wrapper fixes this."""

        def __init__(self, impl):
            self.__impl = impl

        def __call__(self, xctx, inf, func, *args):
            rets = self.__impl(*args)
            try:
                len(rets)
            except TypeError:
                rets = [rets]
            return rets

    # Methods for Infinity function execution.

    def call(self, signature, *args):
        """Call the specified function with the specified arguments."""
        provider, name, ptypes, rtypes \
            = functions.unpack_signature(signature)
        ref = py8x.ctx_get_funcref(self.__ctx,
                                   provider, name,
                                   types.encode(ptypes),
                                   types.encode(rtypes))
        if not py8x.funcref_is_resolved(ref):
            raise UnresolvedFunctionError(signature)

        switch_interpreter = (
            self.tracelevel > 0
            and not py8x.xctx_get_use_debug_interpreter(self.__xctx))
        if switch_interpreter:
            py8x.xctx_set_use_debug_interpreter(self.__xctx, True)
        try:
            return list(py8x.xctx_call(self.__xctx, ref, self.__inf,
                                       tuple(map(self.__wrap_call_arg,
                                                 args))))
        finally:
            if switch_interpreter:
                py8x.xctx_set_use_debug_interpreter(self.__xctx, False)

    def __wrap_call_arg(self, arg):
        """Translate I8X function arguments into libi8x funcrefs."""
        if hasattr(arg, "signature"):
            provider, name, ptypes, rtypes \
                = functions.unpack_signature(arg.signature)
            arg = py8x.ctx_get_funcref(self.__ctx,
                                       provider, name,
                                       types.encode(ptypes),
                                       types.encode(rtypes))
        return arg

    def __read_memory(self, inf, addr, len):
        """Memory reader function."""
        fmt = {1: b"B", 2: b"H", 4: b"I", 8: b"Q"}[len]
        return self.env.read_memory(fmt, addr)

    def __relocate(self, inf, reloc):
        """Address relocation function."""
        func = py8x.reloc_get_func(reloc)
        for name in func.symbols_at[reloc]:
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
        return py8x.to_signed(value)

    def to_unsigned(self, value):
        """Convert a signed integer to the interpreter's representation."""
        return py8x.to_unsigned(value)

    # Methods for the I8C testsuite.

    @property
    def _i8ctest_functions(self):
        functions = py8x.ctx_get_functions(self.__ctx)
        try:
            li = py8x.list_get_first(functions)
            while True:
                yield py8x.listitem_get_object(li)
                li = py8x.list_get_next(functions, li)
        except StopIteration:
            return

class PY8XObject(object):
    """Capsule wrapper required by libi8x-lo."""

    @classmethod
    def new(cls, klass):
        return cls()

    def __init__(self):
        pass

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
            return int(value[2:], 16)
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

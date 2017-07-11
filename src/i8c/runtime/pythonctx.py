# -*- coding: utf-8 -*-
# Copyright (C) 2015-17 Red Hat, Inc.
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
from . import UnresolvedFunctionError
from . import context
from . import functions
from . import stack
import ctypes
import sys

class Context(context.AbstractContext):
    INTERPRETER = "Python interpreter (deprecated)"

    def __init__(self, *args, **kwargs):
        super(Context, self).__init__(*args, **kwargs)
        self.functions = {}
        self.__last_traced = None

    # Methods to populate the context with Infinity functions.

    def import_note(self, ns):
        """Import one note."""
        self.__setup_platform()
        function = functions.BytecodeFunction(ns)
        funclist = self.functions.get(function.signature, [])
        if not funclist:
            self.functions[function.signature] = funclist
        funclist.append(function)

    def __setup_platform(self):
        """Initialize platform-specific stuff as per the first note."""
        if not hasattr(self, "sint_t"):
            self.sint_t = getattr(ctypes, "c_int%d" % self.wordsize)
        if not hasattr(self, "uint_t"):
            self.uint_t = getattr(ctypes, "c_uint%d" % self.wordsize)

    def override(self, function):
        """Register a function, overriding any existing versions."""
        self.functions[function.signature] = [function]

    # Methods for Infinity function execution.

    def call(self, signature, *args):
        """Call the specified function with the specified arguments."""
        function = self.get_function(signature)
        stack = self.new_stack()
        stack.push_multi(reversed(function.ptypes), reversed(args))
        function.execute(self, stack)
        return stack.pop_multi(function.rtypes)

    def get_function(self, sig_or_ref):
        if isinstance(sig_or_ref, functions.UnresolvedFunction):
            reference = sig_or_ref
            signature = reference.signature
        else:
            if isinstance(sig_or_ref, bytes):
                sig_or_ref = sig_or_ref.decode("utf-8")
            signature = sig_or_ref
            reference = None
        assert isinstance(signature, str)
        funclist = self.functions.get(signature, None)
        if funclist is None or len(funclist) != 1:
            raise UnresolvedFunctionError(signature, reference)
        return funclist[0]

    def new_stack(self):
        return stack.Stack(self)

    def __trace(self, location, stack, encoded, decoded):
        function, pc = location
        if self.tracelevel > 0:
            if function != self.__last_traced:
                fprint(sys.stdout, "\n%s:" % function)
                self.__last_traced = function
            if self.tracelevel > 1:
                stack.trace(self.tracelevel)
            fprint(sys.stdout, "  %04x: %-12s %s" % (pc, encoded, decoded))

    def trace_operation(self, *args):
        self.__trace(*args)

    def trace_call(self, function, stack):
        if not isinstance(function, functions.BytecodeFunction):
            if self.tracelevel > 0:
                fprint(sys.stdout, "\n%s:" % function)
                fprint(sys.stdout, "  NON-BYTECODE FUNCTION")
        self.__last_traced = None

    def trace_return(self, location, stack):
        self.__trace(location, stack, "", "RETURN")
        self.__last_traced = None

    # Methods to convert between signed and unsigned integers.

    def to_signed(self, value):
        """Interpret an integer from the interpreter as signed."""
        return self.sint_t(value).value

    def to_unsigned(self, value):
        """Convert a signed integer to the interpreter's representation."""
        return self.uint_t(value).value

    # Methods for the I8C testsuite.

    @property
    def _i8ctest_functions(self):
        result = []
        for list in self.functions.values():
            result.extend(list)
        return result

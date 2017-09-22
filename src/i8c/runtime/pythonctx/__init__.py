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

from ...compat import fprint, str
from .. import UnresolvedFunctionError
from .. import context
from . import functions
from . import stack
import ctypes
import struct
import sys

class Context(context.AbstractContext):
    INTERPRETER = "Python interpreter (deprecated)"
    MAX_WORDSIZE = None  # No maximum.

    def __init__(self, *args, **kwargs):
        super(Context, self).__init__(*args, **kwargs)
        self.functions = {}

    # Methods to populate the context with Infinity functions.

    def import_note(self, ns):
        """Import one note."""
        self.__setup_platform()
        function = functions.BytecodeFunction(ns)
        funclist = self.functions.get(function.signature, [])
        if not funclist:
            self.functions[function.signature] = funclist
        funclist.append(function)
        return function

    def __setup_platform(self):
        """Initialize platform-specific stuff as per the first note."""
        if not hasattr(self, "sint_t"):
            self.sint_t = getattr(ctypes, "c_int%d" % self.wordsize)
        if not hasattr(self, "uint_t"):
            self.uint_t = getattr(ctypes, "c_uint%d" % self.wordsize)

    def override(self, function):
        """Register a function, overriding any existing versions."""
        function = functions.BuiltinFunction(function.signature,
                                             function.impl)
        self.functions[function.signature] = [function]

    # Methods for Infinity function execution.

    def call(self, callee, *args):
        """Call the specified function with the specified arguments."""
        function = self.get_function(callee)
        stack = self.new_stack()
        stack.push_multi(reversed(function.ptypes), reversed(args))
        function.execute(self, stack)
        return stack.pop_multi(function.rtypes)

    def get_function(self, sig_or_ref):
        if isinstance(sig_or_ref, functions.UnresolvedFunction):
            reference = sig_or_ref
        else:
            reference = None
        signature = getattr(sig_or_ref, "signature", sig_or_ref)
        funclist = self.functions.get(signature, None)
        if funclist is None or len(funclist) != 1:
            raise UnresolvedFunctionError(signature, reference)
        return funclist[0]

    def new_stack(self):
        if not hasattr(self, "wordsize"):
            self.wordsize = len(struct.pack("P", 0)) * 8
            self.__setup_platform()
        return stack.Stack(self)

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

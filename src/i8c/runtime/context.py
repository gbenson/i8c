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

from ..compat import fprint, str
from . import *
from . import provider
from . import functions
from . import stack
import sys

class Context(object):
    def __init__(self):
        self.functions = {}
        self.env = None
        self.wordsize = None
        self.byteorder = None
        self.tracelevel = 0
        self.__last_traced = None

    # Methods to XXX

    def register_function(self, function):
        funclist = self.functions.get(function.signature, [])
        if not funclist:
            self.functions[function.signature] = funclist
        funclist.append(function)

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
        # First check for implementations in the testcase.
        # We do this first to allow testcases to override
        # functions which may actually exist.
        if reference is not None:
            impl = "%s_%s_impl" % (reference.provider, reference.name)
            impl = getattr(self.env, impl, None)
            if impl is not None:
                return functions.BuiltinFunction(reference, impl)
        # Now check the registered functions
        funclist = self.functions.get(signature, None)
        if funclist is not None:
            if len(funclist) == 1:
                return funclist[0]
            elif len(funclist) > 1:
                raise AmbiguousFunctionError(sig_or_ref)
        # No registered function with this name
        raise UndefinedFunctionError(sig_or_ref)

    # Methods to XXX

    def import_notes(self, filename):
        with provider.open(filename) as np:
            for note in np.infinity_notes:
                self.import_note(note)

    def import_note(self, note):
        if self.wordsize is None:
            self.wordsize = note.wordsize
        else:
            assert note.wordsize == self.wordsize
        if self.byteorder is None:
            self.byteorder = note.byteorder
        else:
            assert note.byteorder == self.byteorder
        self.register_function(functions.BytecodeFunction(note))

    def new_stack(self):
        return stack.Stack(self.wordsize)

    def call(self, signature, *args):
        function = self.get_function(signature)
        stack = self.new_stack()
        stack.push_multi(reversed(function.ptypes), reversed(args))
        function.execute(self, stack)
        return stack.pop_multi(function.rtypes)

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

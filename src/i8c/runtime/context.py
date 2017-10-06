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

from .core import TestObject
from . import provider
from . import SymbolError, UnhandledNoteError
import sys

class AbstractContext(TestObject):
    INTERPRETER = "UNKNOWN"
    MAX_WORDSIZE = 0

    def __init__(self, env=None):
        super(AbstractContext, self).__init__(env)
        self.tracelevel = 0
        self._i8ctest_reset_symbols()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.finalize()

    def __del__(self):
        self.finalize()

    def finalize(self):
        """Release any resources held by this context."""

    def import_notes(self, filename):
        """Import notes from the specified file."""
        with provider.open(filename) as np:
            for ns in np.infinity_notes:
                self.__setup_platform(ns)
                self.coverage.add_function(self.import_note(ns))

    def __setup_platform(self, ns):
        """Initialize platform-specific stuff as per the first note."""
        if hasattr(self, "wordsize"):
            self.env.assertEqual(ns.wordsize, self.wordsize)
        else:
            self.env.assertIsNotNone(ns.wordsize)
            if (self.MAX_WORDSIZE is not None
                  and self.MAX_WORDSIZE < ns.wordsize):
                msg = getattr(self, "_i8ctest_bad_wordsize_msg", None)
                raise UnhandledNoteError(ns, msg)
            self.wordsize = ns.wordsize

        if hasattr(self, "byteorder"):
            self.env.assertEqual(ns.byteorder, self.byteorder)
        else:
            self.env.assertIn(ns.byteorder, b"<>")
            self.byteorder = ns.byteorder

    def import_note(self, ns): # pragma: no cover
        """Import one note."""
        raise NotImplementedError

    def override(self, function): # pragma: no cover
        """Register a function, overriding any existing versions."""
        raise NotImplementedError

    def call(self, callee, *args): # pragma: no cover
        """Call the specified function with the specified arguments."""
        raise NotImplementedError

    def to_signed(self, value): # pragma: no cover
        """Interpret an integer from the interpreter as signed."""
        raise NotImplementedError

    def to_unsigned(self, value): # pragma: no cover
        """Convert a signed integer to the interpreter's representation."""
        raise NotImplementedError

    def register_symbol(self, name, addr):
        """Associate a symbol name with an address."""
        self.env.assertNotIn(name, self.__symbols)
        self.env.assertIsNotNone(addr)
        self.__symbols[name] = addr

    def lookup_symbol(self, names, error_location):
        """Return the address associated with the specified symbol name."""
        for name in names:
            addr = self.__symbols.get(name, None)
            if addr is not None:
                return addr
        raise SymbolError(error_location, names)

    def _i8ctest_reset_symbols(self):
        """Clear all registered symbols."""
        self.__symbols = {}

    @property
    def _i8ctest_functions(self): # pragma: no cover
        """Iterate over all currently-loaded functions."""
        raise NotImplementedError

    def _trace(self, signature, pc=None, opname=None, stack=None):
        """Hook called every time an instruction is executed."""
        if pc is not None:
            self.coverage.log_operation(signature, pc, opname)
        if self.tracelevel <= 0:
            return
        msg = signature
        if pc is None:
            msg += ": "
        else:
            msg = "%-39s %10s\t" % (msg, hex(pc))
        msg += "%-23s " % opname
        if stack is not None:
            msg += "%4s" % ("[%d]" % len(stack))
            for slot in range(self.tracelevel + 1):
                if len(stack) > slot:
                    value = stack[slot]
                else:
                    value = None

                if value is None:
                    value = "----------"
                else:
                    value = "0x%08x" % value

                msg += "\t%-18s" % value
        self.trace(msg.rstrip())

    def trace(self, msg): # pragma: no cover
        """Display a tracing message to the user."""
        print(msg, file=sys.stderr)

class AbstractOperation(object):
    def __eq__(self, other):
        return not (self != other)

    def __ne__(self, other):
        return (self.fullname != other.fullname
                or self.operands != other.operands)

    @property
    def name(self):
        bits = self.fullname.split("_OP_", 1)
        assert len(bits) == 2
        return bits[1]

    @property
    def operand(self):
        assert len(self.operands) == 1
        return self.operands[0]

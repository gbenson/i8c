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

from . import provider
import sys
import weakref
try:
    import unittest2 as unittest
except ImportError: # pragma: no cover
    import unittest

class FallbackEnvironment(unittest.TestCase):
    """Dummy environment; ensures self.env.assert* always works."""

    def runTest(self):
        self.fail("should not call")

class AbstractContext(object):
    __fallback_env = FallbackEnvironment()

    def __init__(self, env=None):
        self.__env = weakref.ref(env or self.__fallback_env)
        self.tracelevel = 0

    def __del__(self):
        self.finalize()

    def finalize(self):
        """Release any resources held by this context."""

    @property
    def env(self):
        return self.__env() or self.__fallback_env

    @env.setter
    def env(self, value):
        raise RuntimeError

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

    @property
    def _i8ctest_functions(self): # pragma: no cover
        """Iterate over all currently-loaded functions."""
        raise NotImplementedError

    def _trace(self, signature, pc=None, opname=None, stack=None):
        """Hook called every time an instruction is executed."""
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

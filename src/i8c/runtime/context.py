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

class AbstractContext(object):
    def __init__(self, env=None):
        self.__env = env
        self.tracelevel = 0

    @property
    def env(self):
        return self.__env

    @env.setter
    def env(self, value): # pragma: no cover
        raise RuntimeError

    def import_notes(self, filename):
        """Import notes from the specified file."""
        with provider.open(filename) as np:
            for ns in np.infinity_notes:
                self.__setup_platform(ns)
                self.import_note(ns)

    def __setup_platform(self, ns):
        """Initialize platform-specific stuff as per the first note."""
        if hasattr(self, "wordsize"):
            assert ns.wordsize == self.wordsize
        else:
            assert ns.wordsize is not None
            self.wordsize = ns.wordsize

        if hasattr(self, "byteorder"):
            assert ns.byteorder == self.byteorder
        else:
            assert ns.byteorder in b"<>"
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

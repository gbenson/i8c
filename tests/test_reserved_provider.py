# -*- coding: utf-8 -*-
# Copyright (C) 2015-16 Red Hat, Inc.
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

from tests import TestCase
from i8c.compiler import ReservedIdentError

SOURCE = """\
define %s::test_reserved_provider returns ptr
    argument ptr __some_symbol
"""

class TestReservedProvider(TestCase):
    """Check that reserved provider names are rejected."""

    def test_reserved_provider(self):
        """Check that reserved provider names are rejected."""
        for provider in ("test", "libpthread", "i8test",
                         "i8core", "i8", "hello"):
            source = SOURCE % provider
            if provider.startswith("i8"):
                self.assertRaises(ReservedIdentError, self.compile, source)
            else:
                tree, output = self.compile(source)
                self.assertEqual([], output.opnames)

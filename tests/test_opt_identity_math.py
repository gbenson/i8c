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

SOURCE = """\
define test::optimize_use_plus_uconst returns int
    argument int x

    load %s
    %s
"""

IDENTITIES = (("add", 0), ("sub", 0),
              ("mul", 1), ("div", 1),
              ("shl", 0), ("shr", 0),
              ("shra", 0), ("or", 0),
              ("xor", 0))

class TestEliminateIdentityMath(TestCase):
    def test_eliminate_identity_math(self):
        """Check that identity math and logic are eliminated."""
        for op, identity in IDENTITIES:
            tree, output = self.compile(SOURCE % (identity, op))
            self.assertEqual(len(output.ops), 0)

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
from i8c.compiler import StackError

# All binary operations were considered equal to each other: the "mul"
# and "add" were considered equivalent and the branch optimized away.

SOURCE = """\
define test::i8cfail_0003 returns int
    argument int y
    argument int z

    load 0
    beq label

    load 0
    mul
    return

label:
    load 1
    add
"""

class TestI8CFail0003(TestCase):
    def test_i8cfail_0003(self):
        """Miscellaneous I8C failure #0003 check"""
        tree, output = self.compile(SOURCE)
        ops = output.opnames
        # Robust test: check the stream contains a branch
        self.assertIn("bra", ops)
        # Fragile test: check that the stream is as we expect.
        # This may need fixing up to cope with future compiler changes.
        self.assertEqual(["bra",
                          "plus_uconst", "skip",
                          "lit0", "mul"], ops)

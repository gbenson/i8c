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
define test::stack_ops_test
    argument int arg_1
    argument ptr arg_2
    argument bool arg_3

    dup
    drop
    pick 0
    pick 1
    pick 2
    over
    swap
    rot
"""

class TestStackOperations(TestCase):
    def test_stack_ops(self):
        """Basic checks for stack-manipulation bytecodes."""
        tree, output = self.compile(SOURCE)
        # Check the assembler contains the expected operations
        self.assertEqual(["dup",
                          "drop",
                          "dup",    # pick 0
                          "over",   # pick 1
                          "pick",   # pick 2
                          "over",
                          "swap",
                          "rot"], output.opnames)

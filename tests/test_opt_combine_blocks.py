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
define test::combine_blocks returns int
    argument int arg1
    argument int arg2

    load arg1
    bge 5, split_1a
    goto split_1b

split_1a:
    load arg2
    blt 4, split_2a
    goto split_2b

split_1b:
    load arg2
    bgt 2, split_2c
    goto split_2d

split_2a:
    load 23
    return

split_2b:
    load 16
    return

split_2c:
    load 16
    return

split_2d:
    load arg1
    add arg2
    bge 1, split_3
    goto split_1a

split_3:
    load 23
    return
"""

class TestCombineBlocks(TestCase):
    def test_combine_blocks(self):
        """Basic block-combiner test."""
        tree, output = self.compile(SOURCE)
        ops = output.opnames
        # Robust test: check the stream contains only one lit16
        # and only one lit23.
        self.assertEqual(len([op for op in ops if op == "lit16"]), 1)
        self.assertEqual(len([op for op in ops if op == "lit23"]), 1)
        # Fragile test: check that the stream is as we expect.
        # This may need fixing up to cope with future compiler changes.
        self.assertEqual(["over", "lit5", "lt", "bra", "dup", "lit4",
                          "ge", "bra", "lit23", "skip", "lit16", "skip",
                          "dup", "lit2", "le", "bra", "skip", "over",
                          "over", "plus", "lit1", "lt", "bra", "skip"],
                         output.opnames)

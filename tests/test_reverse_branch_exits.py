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
define test::optimize_reverse_branch_exits returns int
    argument int x

    load 1
    bne label1
    goto label2
label1:
    load 2
    return
label2:
    load 3
"""

class TestOptimizeReverseBranchExits(TestCase):
    def test_optimize_reverse_branch_exits(self):
        """Check we don't emit "bra, skip" if we don't need to."""
        tree, output = self.compile(SOURCE)
        self.assertEqual(["lit1", "eq", "bra",
                          "lit2", "skip",
                          "lit3"], output.opnames)

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

SOURCE1 = """\
define test::optimize_cmp_bra_const_const returns ptr
    argument ptr x

    dup
    load NULL
    beq return_the_null
    deref ptr
    return
return_the_null:
"""

SOURCE2 = """\
define test::optimize_cmp_bra_const_const returns ptr
    argument ptr x

    dup
    load NULL
    bne dereference
    return
dereference:
    deref ptr
"""

class TestOptimizeLit0CmpBeforeBra(TestCase):
    def test_optimize_lit0_cmp_before_bra(self):
        """Check that lit0,cmp before bra is eliminated."""
        for source in SOURCE1, SOURCE2:
            tree, output = self.compile(source)
            self.assertEqual(["dup", "bra", "skip", "deref"], output.opnames)

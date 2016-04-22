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
define test::dup_over_equiv returns int
    argument int x
    argument int y
    argument int z

    blt 5, label

    load 0
    %s
    return

label:
    load 1
    pick %d
"""

class TestDupOverEquiv(TestCase):
    def test_dup_over_equiv(self):
        """Check that dup and over are equivalent to picks."""
        for equiv, index in (("dup", 0), ("over", 1)):
            tree, output = self.compile(SOURCE % (equiv, index))
            self.assertEqual(["lit5", "lt", equiv], output.opnames)

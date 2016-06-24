# -*- coding: utf-8 -*-
# Copyright (C) 2016 Red Hat, Inc.
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

# XXX what?

SOURCE = """\
define test::i8xfail_0002 returns int
    extern ptr sym1
    deref sym1, uint32_t
"""

class TestI8XFail0002(TestCase):
    def test_i8xfail_0002(self):
        """Miscellaneous I8X failure #0002 check"""
        tree, output = self.compile(SOURCE)
        EXPECT = 0xdeadbeef
        with self.memory.builder() as mem:
            sym1 = mem.alloc("sym1")
            sym1.store_u32(0, EXPECT)
        self.assertEqual(output.call("test::i8xfail_0002()i"), [EXPECT])

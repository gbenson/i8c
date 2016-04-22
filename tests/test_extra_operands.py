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
from i8c.compiler import ParserError

SOURCE_0arg = """\
define test::extra_operands_0 returns int
    argument int x
    dup junk
"""

SOURCE_1arg = """\
define test::extra_operands_1 returns int
    argument ptr x
    pick 5, junk
label:
"""

SOURCE_2arg = """\
define test::extra_operands_2 returns int
    argument ptr x
    cast x, int, junk
"""

class TestExtraOperands(TestCase):
    def test_extra_operands(self):
        """Ensure the parser detects extra operands."""
        for source in SOURCE_0arg, SOURCE_1arg, SOURCE_2arg:
            self.assertRaises(ParserError, self.compile, source)

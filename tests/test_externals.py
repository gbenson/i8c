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
define test::externals_test returns int
    extern ptr a_symbol
    extern func int, int (ptr) a_function
    load a_symbol
    call a_function
"""

SOURCE2 = """\
typedef ptr ptr_alias_t
typedef func int, int (ptr) fun_alias_f

define test::externals_test returns int
    extern ptr_alias_t a_symbol
    extern fun_alias_f a_function
    load a_symbol
    call a_function
"""

class TestExternals(TestCase):
    def test_externals(self):
        """Check that externals work."""
        for source in SOURCE1, SOURCE2:
            tree, output = self.compile(source)
            self.assertEqual(
                ["addr", "load_external", "call"],
                output.opnames)

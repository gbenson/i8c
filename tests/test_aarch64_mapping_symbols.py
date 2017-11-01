# -*- coding: utf-8 -*-
# Copyright (C) 2017 Red Hat, Inc.
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

# The precompiled shared library is from a Fedora 26 aarch64 run of
# I8C's test_relocation testcase.  The test fail because binaries on
# aarch64 may have extra symbols ("mapping symbols") that need to be
# skipped.

from tests import TestCase
from i8c.runtime import Context, coverage
import os

class TestAarch64MappingSymbols(TestCase):
    def test_aarch64_mapping_symbols(self):
        """Check that aarch64 mapping symbols are skipped."""
        output = self.load_precompiled()
        self.assertEqual(output.ops[0].operand, ["a_symbol"])

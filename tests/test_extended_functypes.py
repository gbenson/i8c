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
typedef uintptr_t size_t
typedef size_t tls_modid_t
typedef ptr link_map_t

extern func link_map_t map, size_t gen (tls_modid_t modid) rtld::__dtv_slotinfo

define test::function returns link_map_t lm, size_t modgen
  argument tls_modid_t modid
  call rtld::__dtv_slotinfo
"""

class TestExtendedFuncTypes(TestCase):
    def test_extended_func_types(self):
        """Check that extended function types work."""
        tree, output = self.compile(SOURCE)
        self.assertEqual(["load_external", "call"], output.opnames)

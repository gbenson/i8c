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

# The precompiled object file is from a Fedora 26 ppc64 build of glibc
# on the infinity-forth-bridge branch.  The static nptl tests failed
# with error: unresolved symbol ‘stack_cache’.  GLIBC is LGPL 2.1+.

from tests import TestCase, multiplexed
from i8c.runtime import SymbolError
import os

class TestI8XFail0003(TestCase):
    @TestCase.provide("procservice::getpid()i")
    def __ps_getpid(self):
        self.fail("should not call")

    @TestCase.provide("test::callback(po)i")
    def callback(self, *args):
        self.fail("should not call")

    def test_i8xfail_0003(self):
        """Miscellaneous I8X failure #0003 check"""
        output = self.load_precompiled()
        self.__input_file = output.variants[0].build.asm_output_file
        self.__test_i8xfail_0003(output)

    @multiplexed
    def __test_i8xfail_0003(self, output):
        with self.assertRaises(SymbolError) as cm:
            output.call("thread::iterate(Fi(po)oi)i",
                        self.callback, 23, 23)
        self.assertEqual(cm.exception.args[0],
                         self.__input_file + "[0x00003332]: " +
                         "error: unresolved symbol ‘stack_used’")

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

from tests import TestCase

CALL_EXTERN_SOURCE = """\
define test::call_extern returns ptr
    argument int arg
    extern func ptr (int) f2c
    call f2c
"""

CALL_ARGUMENT_SOURCE = """\
define test::call_argument returns ptr
    argument func ptr (int) fn
    argument int arg
    swap
    call
"""

class UserFuncTestCase(object):
    """Test the @TestCase.provide decorator."""

    def test_call_direct(self):
        """Test calling a user function directly."""
        tree, output = self.compile("define ju::nk")
        self.assertEqual(output.call(self.userfunc, 32), [0])

    def test_call_arg(self):
        """Test calling a user function passed as an argument."""
        tree, output = self.compile(CALL_ARGUMENT_SOURCE)
        self.assertEqual(output.call(output.note.signature,
                                     self.userfunc, 0),
                         [output.to_unsigned(-18)])

class TestGlobalUserFunctions(TestCase, UserFuncTestCase):
    @TestCase.provide("test::f2c(i)p")
    def userfunc(self, arg):
        return self.to_unsigned((self.to_signed(arg) - 32) * 5 // 9)

    def test_call_direct_by_name(self):
        """Test calling a user function by name."""
        tree, output = self.compile("define ju::nk")
        self.assertEqual(output.call(self.userfunc.signature, 212),
                         [100])

    def test_call_external(self):
        """Test calling a user function via an external reference."""
        tree, output = self.compile(CALL_EXTERN_SOURCE)
        self.assertEqual(output.call(output.note.signature, 451),
                         [232])

    def test_call_arg_by_name(self):
        """Test calling a user function passed as an argument by name."""
        tree, output = self.compile(CALL_ARGUMENT_SOURCE)
        self.assertEqual(output.call(output.note.signature,
                                     self.userfunc.signature,
                                     output.to_unsigned(-459)),
                         [output.to_unsigned(-273)])

class TestLocalUserFunctions(TestCase, UserFuncTestCase):
    @TestCase.provide("::(i)p")
    def userfunc(self, arg):
        return self.to_unsigned((self.to_signed(arg) - 32) * 5 // 9)

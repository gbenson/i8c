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
from i8c.compiler import ParserError, RedefinedIdentError

SOURCE = """\
define test::load_slot
   argument int an_argument
   extern ptr a_symbol
   extern func () a_function
   extern func () other_provider::function_2
   load a_symbol
   load a_function
   load other_provider::function_2
"""

SOURCE_NAMES_SLOTS = (("an_argument", 3),
                      ("a_symbol", 2),
                      ("a_function", 1),
                      ("test::a_function", 1),
                      ("other_provider::function_2", 0))

SOURCE_WITH_NAME = SOURCE + """\
   load 23
   name 0, a_name
"""

SWN_NAMES_SLOTS = (("an_argument", 4),
                   ("a_symbol", 3),
                   ("a_function", 2),
                   ("test::a_function", 2),
                   ("other_provider::function_2", 1),
                   ("a_name", 0))

class TestLoadSlot(TestCase):
    def test_shortname_only(self):
        """Check that name rejects fullnames."""
        source = SOURCE + "name 2 provider::shortname"
        self.assertRaises(ParserError, self.compile, source)

    def test_basic(self):
        """Check externals' names work."""
        for name, expect_slot in SOURCE_NAMES_SLOTS:
            source = SOURCE + "load " + name
            tree, output = self.compile(source)
            ops = output.ops
            self.assertEqual(len(ops), 4)
            op = ops[-1]
            if expect_slot == 0:
                self.assertEqual(op.name, "dup")
            elif expect_slot == 1:
                self.assertEqual(op.name, "over")
            else:
                self.assertEqual(op.name, "pick")
                self.assertEqual(op.operand, expect_slot)

    def test_name_anonymous_slot(self):
        """Check naming anonymous slots works."""
        for name, expect_slot in SWN_NAMES_SLOTS:
            tree, output = self.compile(SOURCE_WITH_NAME + "load " + name)
            ops = output.ops
            self.assertEqual(len(ops), 5)
            op = ops[-1]
            if expect_slot == 0:
                self.assertEqual(op.name, "dup")
            elif expect_slot == 1:
                self.assertEqual(op.name, "over")
            else:
                self.assertEqual(op.name, "pick")
                self.assertEqual(op.operand, expect_slot)

    def test_name_named_slot(self):
        """Check naming already-named slots works."""
        for name, expect_slot in SOURCE_NAMES_SLOTS:
            names = ["a_name", name]
            for order in 0, 1:
                source = SOURCE + "\n".join(
                    ["name %d, a_name" % expect_slot]
                    + ["load %s" % name for name in names])
                tree, output = self.compile(source)
                ops = output.ops
                self.assertEqual(len(ops), 5)

                # The first load can pick from anywhere
                op = ops[-2]
                if expect_slot == 0:
                    self.assertEqual(op.name, "dup")
                elif expect_slot == 1:
                    self.assertEqual(op.name, "over")
                else:
                    self.assertEqual(op.name, "pick")
                    self.assertEqual(op.operand, expect_slot)

                # The second load should grab the top slot
                self.assertEqual(ops[-1].name, "dup")

                names.reverse()

    def test_shadowing_rename(self):
        """Check that you cannot shadow slots."""
        for name, expect_slot in SWN_NAMES_SLOTS:
            if name.find("::") >= 0:
                continue
            assert expect_slot != 1
            source = SOURCE_WITH_NAME + "name 1, %s" % name
            self.assertRaises(RedefinedIdentError, self.compile, source)

    def test_existing_name(self):
        """Check that giving a slot its existing name is ok."""
        for name, expect_slot in SWN_NAMES_SLOTS:
            if name.find("::") >= 0:
                continue
            source = SOURCE_WITH_NAME + "\n".join(
                ["name %d, %s" % (expect_slot, name),
                 "load %s" % name])
            tree, output = self.compile(source)
            ops = output.ops
            self.assertEqual(len(ops), 5)
            op = ops[-1]
            if expect_slot == 0:
                self.assertEqual(op.name, "dup")
            elif expect_slot == 1:
                self.assertEqual(op.name, "over")
            else:
                self.assertEqual(op.name, "pick")
                self.assertEqual(op.operand, expect_slot)

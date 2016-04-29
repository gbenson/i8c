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

# Operators which can have folded loads

comparisons = ("lt", "le", "eq", "ne", "ge", "gt")

BINARY_OPS = ("add", "and", "div", "mod", "mul",
              "shl", "shr", "shra", "sub", "xor") + comparisons

BRANCH_OPS = tuple("b" + op for op in comparisons)

# Sources for the various tests

BINARY_SOURCE = """\
define test::fold_load_test returns int
    argument int x
    %s
"""

BRANCH_SOURCE = BINARY_SOURCE + """\
    load 0
    return
label:
    load 1
    return
"""

CALL_SOURCE = """\
define test::fold_load_test
    %s
"""

DEREF_SOURCE = """\
define test::fold_load_test returns ptr
    extern ptr p
    %s
"""

class TestFoldLoad(TestCase):
    def test_binary_fold_load(self):
        """Check that folded loads work for binary operations."""
        self.__do_test(BINARY_SOURCE, BINARY_OPS, "5")

    def test_branch_fold_load(self):
        """Check that folded loads work for conditional branches."""
        self.__do_test(BRANCH_SOURCE, BRANCH_OPS, "5", "label")

    def test_call_fold_load(self):
        """Check that folded loads work for "call"."""
        self.__do_test(CALL_SOURCE, ("call",), "fold_load_test")

    def test_deref_fold_load(self):
        """Check that folded loads work for "deref"."""
        self.__do_test(DEREF_SOURCE, ("deref",), "p", "ptr")

    def __do_test(self, source, ops, load_arg, extra=None):
        for op in ops:
            expect_ops = [{"call": "load_external",
                           "deref": "addr"}.get(op, "lit%s" % load_arg),
                          {"add": "plus",
                           "sub": "minus"}.get(op, op)]
            if expect_ops[1] == "plus":
                expect_ops = ["plus_uconst"]
            elif expect_ops[1] in BRANCH_OPS:
                expect_ops[1] = expect_ops[1][1:]

            sub1 = "load %s\n    %s" % (load_arg, op)
            sub2 = "%s %s" % (op, load_arg)
            if extra is not None:
                sub1 += " " + extra
                sub2 += ", " + extra

            for sub in sub1, sub2:
                tree, output = self.compile(source % sub)
                self.assertEqual(expect_ops, output.opnames)

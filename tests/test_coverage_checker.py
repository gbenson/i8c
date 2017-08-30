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

SOURCE = """\
define test::coverage_me returns int
  argument ptr addr
  deref int8_t
  dup
  blt 0, label
  dup
  add
  return
label:
  neg
"""

class TestCoverageChecker(TestCase):
    def setUp(self):
        tree, self.output = self.compile(SOURCE)
        self.addCleanup(delattr, self, "output")
        self.assertEqual(len(self.coverage.functions), 1)

        # deref_int was chosen because libi8x rewrites it.
        self.assertEqual(self.output.opnames[0], "deref_int")

    @property
    def coverage(self):
        return self.output.coverage

    def test_repeat_adds(self):
        """Test adding the same function a second time."""
        saved_ops = list(self.coverage.functions.values())[0].ops.copy()
        func1 = self.output.note

        # Compile the same code a second time.
        tree, output = self.compile(SOURCE)
        func2 = output.note
        del tree, output
        self.assertIsNot(func2, func1)

        # Ensure the signatures are the same.
        self.assertEqual(func2.signature, func1.signature)

        # Ensure the sets of operations are different but equal.
        ops1, ops2 = func1.ops, func2.ops
        self.assertIsNot(ops1, ops2)
        self.assertEqual(ops1, ops2)
        for pc in ops1:
            self.assertIsNot(ops1[pc], ops2[pc])

        # Add the same-but-different function (twice for good measure).
        for i in range(2):
            self.coverage.add_function(func2)

        # Check nothing changed in the accumulator.
        self.assertEqual(len(self.coverage.functions), 1)
        check_ops = list(self.coverage.functions.values())[0].ops
        self.assertIsNot(saved_ops, check_ops)
        self.assertEqual(saved_ops, check_ops)
        for pc in saved_ops:
            self.assertIs(saved_ops[pc], check_ops[pc])

    def test_bad_repeat_add(self):
        """Test adding a different function with the same signature."""
        func = self.output.note
        class TestFunc(object):
            signature = func.signature
            coverage_ops = dict(list(func.coverage_ops.items())[:-1])
        with self.assertRaises(AssertionError):
            self.coverage.add_function(TestFunc)

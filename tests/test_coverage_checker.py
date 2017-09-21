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

from tests import TestCase, multiplexed

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
  warn "it's negative"
  neg
"""

class TestCoverageChecker(TestCase):
    def setUp(self):
        tree, self.output = self.compile(SOURCE)
        self.addCleanup(delattr, self, "output")
        self.assertEqual(len(self.coverage.functions), 1)

        # Sanity checks:
        # - deref_int was chosen because libi8x rewrites it.
        # - warn was chosen because its operand is a string.
        opnames = self.output.opnames
        self.assertGreater(len(opnames), 8)
        self.assertEqual(opnames[0], "deref_int")
        self.assertEqual(opnames[8], "warn")

        self.__setup_memory()

    @multiplexed
    def __setup_memory(self):
        with self.memory.builder() as mem:
            addr = mem.alloc()
            addr.store_i8(0, 1)
            addr.store_i8(1, -1)
        self.addr = addr.location

    @property
    def coverage(self):
        return self.output.coverage

    @property
    def opcount(self):
        return len(self.output.note.coverage_ops)

    def warn_caller(self, *args):
        self.assertEqual(args, ("test::coverage_me(p)i", "it's negative"))

    @multiplexed
    def test_repeat_adds(self):
        """Test adding the same function a second time."""
        saved_ops = list(self.coverage.functions.values())[0].ops.copy()
        func1 = self.output.note

        # Compile the same code a second time.
        tree, output = self.compile(SOURCE)
        func2 = output.variants[self.variant_index].note
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

    @multiplexed
    def test_bad_repeat_add(self):
        """Test adding a different function with the same signature."""
        func = self.output.note
        class TestFunc(object):
            signature = func.signature
            coverage_ops = dict(list(func.coverage_ops.items())[:-1])
        with self.assertRaises(AssertionError):
            self.coverage.add_function(TestFunc)

    def test_zero_coverage(self):
        """Test coverage accessors with 0% coverage."""
        self.__check_report(True, False)

    def test_full_coverage(self):
        """Test coverage accessors with 100% coverage."""
        self.output.call("test::coverage_me(p)i", self.addr)
        self.output.call("test::coverage_me(p)i", self.addr + 1)
        self.__check_report(False, True)

    def test_intermediate_coverage(self):
        """Test coverage accessors with 0% < x < 100% coverage."""
        self.output.call("test::coverage_me(p)i", self.addr)
        self.__check_report(False, False)

    @multiplexed
    def __check_report(self, expect_zero, expect_full):
        self.assertFalse(expect_zero and expect_full)
        self.assertEqual(self.coverage.is_total, expect_full)

        report = self.coverage.report
        self.assertEqual(len(report), 1)
        [sig] = report.keys()
        self.assertEqual(sig, "test::coverage_me(p)i")
        counts = report.pop(sig)
        self.assertEqual(len(counts), 2)
        hit, missed = counts
        self.assertEqual(hit + missed, self.opcount)
        self.assertEqual(hit == 0, expect_zero)
        self.assertEqual(hit == self.opcount, expect_full)
        if not expect_zero:
            self.assertGreater(hit, missed)

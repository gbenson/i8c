# -*- coding: utf-8 -*-
# Copyright (C) 2017 Red Hat, Inc.
# This file is part of the Infinity Note Execution Environment.
#
# The Infinity Note Execution Environment is free software; you can
# redistribute it and/or modify it under the terms of the GNU Lesser
# General Public License as published by the Free Software Foundation;
# either version 2.1 of the License, or (at your option) any later
# version.
#
# The Infinity Note Execution Environment is distributed in the hope
# that it will be useful, but WITHOUT ANY WARRANTY; without even the
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with the Infinity Note Execution Environment; if not,
# see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

class Accumulator(object):
    def __init__(self):
        self.functions = {}

    def add_function(self, func):
        self.__add_function(func.signature, func.coverage_ops)

    def __add_function(self, sig, ops):
        func = self.functions.get(sig, None)
        if func is None:
            self.functions[sig] = Function(ops)
        else:
            func.assertOpsEqual(ops)

    def log_operation(self, sig, pc, opname):
        self.functions[sig].log_operation(pc, opname)

    @property
    def is_total(self):
        """True if 100% coverage has been acheived, False otherwise."""
        for func in self.functions.values():
            if func.has_missed_ops:
                return False
        return True

    @property
    def report(self):
        return dict((s, f.report) for s, f in self.functions.items())

class Function(object):
    def __init__(self, ops):
        for op in ops.values():
            assert not hasattr(op, "hitcount")
            op.hitcount = 0
        self.ops = ops

    def assertOpsEqual(self, ops):
        assert ops == self.ops

    def log_operation(self, pc, opname):
        op = self.ops[pc]
        assert op.fullname == opname
        op.hitcount += 1

    @property
    def has_missed_ops(self):
        """False if 100% coverage has been acheived, True otherwise."""
        for op in self.ops.values():
            if op.hitcount < 1:
                return True
        return False

    @property
    def report(self):
        hit = missed = 0
        for op in self.ops.values():
            if op.hitcount < 1:
                missed += 1
            else:
                hit += 1
        return hit, missed

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

class Function(object):
    def __init__(self, ops):
        self.ops = ops

    def assertOpsEqual(self, ops):
        assert ops == self.ops

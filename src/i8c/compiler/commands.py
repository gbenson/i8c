# -*- coding: utf-8 -*-
# Copyright (C) 2016 Red Hat, Inc.
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

import os

class Variable(object):
    def __init__(self, name, default):
        self.as_str = os.environ.get(name, default)
        self.as_list = self.as_str.split()

    def __str__(self):
        return self.as_str

    def __add__(self, other):
        assert isinstance(other, list)
        return self.as_list + other


# Program for compiling C programs.
I8C_CC = Variable("I8C_CC", "gcc")

# Program for running the C preprocessor, with results to standard output.
I8C_CPP = Variable("I8C_CPP", "%s -E -x assembler-with-cpp" % I8C_CC)

# Program for compiling assembly files.
I8C_AS = Variable("I8C_AS", "%s -x assembler-with-cpp" % I8C_CC)

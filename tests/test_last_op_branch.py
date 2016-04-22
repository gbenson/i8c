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
define test::last_op_is_branch
    argument bool x
    argument bool y

    goto label2
label1:
    return

label2:
    bne label1
"""

class TestFuncWithLastOpBra(TestCase):
    def test_last_op_is_branch(self):
        """Check that functions whose last op is a branch work.

        This is testing the code that adds the synthetic return.
        As a side-effect it also exercises the code that stops
        us generating unnecessary gotos.
        """
        tree, output = self.compile(SOURCE)
        self.assertEqual(["ne", "bra"], output.opnames)

# -*- coding: utf-8 -*-
# Copyright (C) 2015 Red Hat, Inc.
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
from i8c.compiler import loggers
import io
import sys

SOURCE = """\
define test::factorial returns int
    argument int x
    extern func int (int) factorial

    swap
    dup
    load 1
    bgt not_done_yet
    load 1
    return

not_done_yet:
    dup
    load 1
    sub
label: // ensure we hit the 1-exit case in blocks.Block.__str_
    swap
    rot
    swap
    call
    mul
"""

EXTERN0_NODE = """\
External
  FuncType [func int (int)]
    ReturnTypes
      BasicType: int [int]
    ParamTypes
      BasicType: int [int]
  ShortName: factorial"""

class TestDebugCode(TestCase):
    """Test various bits of debugging code."""

    def setUp(self):
        self.disable_loggers()
        self.saved_stderr = sys.stderr

    def tearDown(self):
        self.disable_loggers()
        sys.stderr = self.saved_stderr

    def test_loggers(self):
        """Exercise all the debug printers."""
        for logger in loggers.values():
            logger.enable()
        sys.stderr = io.StringIO()
        self.compile(SOURCE)

    def test_str_methods(self):
        """Check various __str__ methods."""
        tree, output = self.compile(SOURCE)
        func = list(tree.functions)[0]
        # lexer.Token.__str__
        token = func.operations.tokens[0]
        self.assertEqual(str(token), "<testcase>:5: 'swap'")
        # parser.TreeNode.__str__ with an annotated type
        node = func.externals.children[0]
        self.assertEqual(str(node), EXTERN0_NODE)
        # blocks.Block.__str_
        blocks = sorted(self.collect_blocks(func).items())
        for index, block in blocks:
            self.assertTrue(str(block).startswith("Block #%d " % index))

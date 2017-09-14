# -*- coding: utf-8 -*-
# Copyright (C) 2016-17 Red Hat, Inc.
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
define test::test_warn returns ptr
    argument ptr arg
    dup
    bne NULL, label
    warn "hello world"
    warn ""
    warn "it's \\"NULL\\""
label:
"""

class TestWarn(TestCase):
    """Check warnings."""

    def warn_caller(self, *args):
        self.warnings.append(args)

    def test_warning(self):
        """Basic check of a warning."""
        tree, output = self.compile(SOURCE)
        self.__test_warning(output)

    @multiplexed
    def __test_warning(self, output):
        self.warnings = []
        output.call("test::test_warn(p)p", 5)
        self.assertEqual(self.warnings, [])
        output.call("test::test_warn(p)p", 0)
        self.assertEqual(self.warnings, [
            ("test::test_warn(p)p", "hello world"),
            ("test::test_warn(p)p", ""),
            ("test::test_warn(p)p", 'it\'s "NULL"')])

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
from i8c.compiler import RedefinedIdentError
from i8c.compiler import UndefinedIdentError

UNDEF_SOURCE = """\
define test::test_label
    goto label
"""

VALID_SOURCE = UNDEF_SOURCE + "label:\n"
REDEF_SOURCE = VALID_SOURCE + "label:\n"

class TestLabels(TestCase):
    """Check that undefined and duplicate labels are caught."""

    def test_valid(self):
        """Basic check of a valid label."""
        tree, output = self.compile(VALID_SOURCE)
        self.assertEqual([], output.opnames)

    def test_undefined(self):
        """Check that references to undefined labels are caught."""
        self.assertRaises(UndefinedIdentError, self.compile, UNDEF_SOURCE)

    def test_redefined(self):
        """Check that duplicate labels are inhibited."""
        self.assertRaises(RedefinedIdentError, self.compile, REDEF_SOURCE)

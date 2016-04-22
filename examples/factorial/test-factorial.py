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

from i8c.runtime import TestCase

class TestFactorial(TestCase):
    TESTFUNC = "example::factorial(i)i"

    def test_factorial(self):
        """Test example::factorial"""
        for x, expect in ((0, 1), (1, 1), (12, 479001600)):
            result = self.i8ctx.call(self.TESTFUNC, x)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0], expect)

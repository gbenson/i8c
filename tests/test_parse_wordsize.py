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

from tests import TestCase
from i8c.compiler import ParserError
import itertools

LINES = ("wordsize %s",
         "typedef int size_t",
         "extern ptr __stack_user",
         "extern func pid_t () procservice::getpid",
         "define test::test_wordsize returns int")

class TestParseWordsize(TestCase):
    """Check that wordsize is only allowed at the start of the input."""

    def test_parse_wordsize(self):
        """Check that wordsize is parsed correctly"""
        for lines in itertools.permutations(LINES):
            srcfmt = "\n".join(lines) + "\n"
            for wordsize in (32, "word", "extern", "typedef", "define"):
                source = srcfmt % wordsize
                # Test with one wordsize directive
                self.__one_test(source, True)
                # Test with two wordsize directives
                self.__one_test("wordsize 32\n" + source, False)

    def __one_test(self, source, maybe_valid):
        is_valid = maybe_valid and source.startswith("wordsize 32\n")
        if not is_valid:
            self.assertRaises(ParserError, self.compile, source)
        else:
            try:
                self.compile(source)
            except ParserError as e:
                self.fail("the parser should accept this")
            except:
                pass
            else:
                self.fail("should have failed somewhere in the compiler")

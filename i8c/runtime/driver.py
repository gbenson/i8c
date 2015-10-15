# -*- coding: utf-8 -*-
# Copyright (C) 2015 Red Hat, Inc.
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

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from .. import cmdline
from ..compat import fprint
from . import context
from . import I8XError
from . import TestCase
import getopt
import imp
import os
import sys
try:
    import unittest2 as unittest
except ImportError: # pragma: no cover
    import unittest

USAGE = """\
Usage: i8x [OPTION]... TESTFILE...
   or: i8x [OPTION]... [-q|--quick] FUNCTION [ARGUMENT]...

Infinity Note Execution Environment.

Options:
  --help                Display this information.
  --version             Display version information.
  -I DIR                Add the directory DIR to the list of directories
                        that TestCase.import_constants_from will search
                        for header files.
  -i, --import=ELFFILE  Import notes from ELFFILE.
  -q, --quick           Execute the function and arguments specified on
                        command line.
  -t, --trace           Trace function execution.  This option may be
                        specified multiple times for greater detail.""" \
    + cmdline.usage_message_footer()

LICENSE = ("LGPLv2.1+: GNU LGPL version 2.1 or later",
           "http://www.gnu.org/licenses/lgpl-2.1.html")

class TestSuite(unittest.TestSuite):
    def __init__(self, *args, **kwargs):
        unittest.TestSuite.__init__(self, *args, **kwargs)
        self.__loader = unittest.TestLoader()

    def load_i8tests(self, ctx, filename):
        name = os.path.splitext(os.path.basename(filename))[0]
        module = imp.load_source(name, filename)
        for name in dir(module):
            item = getattr(module, name)
            if (item is not TestCase
                and type(item) is type
                and issubclass(item, TestCase)):
                self.addTest(self.__loader.loadTestsFromTestCase(item))

def main(args):
    try:
        opts, args = getopt.gnu_getopt(
            args,
            "i:I:qt",
            ("help", "version", "import=", "quick", "trace"))
    except getopt.GetoptError as e:
        raise I8XError("%s\nTry ‘i8x --help’ for more information." % e)
    ctx = context.Context()
    quickmode = False
    for opt, arg in opts:
        if opt == "--help":
            fprint(sys.stdout, USAGE)
            return
        elif opt == "--version":
            fprint(sys.stdout, cmdline.version_message_for("i8x", LICENSE))
            return
        elif opt == "-I":
            TestCase.include_path.append(arg)
        elif opt in ("-i", "--import"):
            ctx.import_notes(arg)
        elif opt in ("-q", "--quick"):
            quickmode = True
        elif opt in ("-t", "--trace"):
            ctx.tracelevel += 1

    if len(args) < 1:
        raise I8XError("nothing to do!")

    if quickmode:
        function = args.pop(0)
        args = [int(arg, 0) for arg in args]
        result = map(str, ctx.call(function, *args))
        fprint(sys.stdout, ", ".join(result))
        return

    TestCase.i8ctx = ctx

    tests = TestSuite()
    for filename in args:
        tests.load_i8tests(ctx, filename)

    unittest.TextTestRunner().run(tests)

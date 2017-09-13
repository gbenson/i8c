# -*- coding: utf-8 -*-
# Copyright (C) 2015-17 Red Hat, Inc.
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

from .. import cmdline
from .. import version
from ..compat import fprint, load_module_from_source, strtoint_c
from . import Context
from . import coverage
from . import I8XError
from . import TestCase
from .core import unittest
import getopt
import os
import sys

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
    + cmdline.usage_message_footer_for("I8X")

LICENSE = ("LGPLv2.1+: GNU LGPL version 2.1 or later",
           "http://www.gnu.org/licenses/lgpl-2.1.html")

def module_install_command(module):
    dir = os.path.dirname(os.path.realpath(sys.executable))
    for cmd in ("pip", "pip3"):
        cmd = os.path.join(dir, cmd)
        if os.path.exists(cmd):
            return "%s install %s" % (cmd, module)
    for cmd in ("easy_install",):
        cmd = os.path.join(dir, cmd)
        if os.path.exists(cmd):
            return "%s %s" % (cmd, module)

class TestSuite(unittest.TestSuite):
    def __init__(self, *args, **kwargs):
        unittest.TestSuite.__init__(self, *args, **kwargs)
        self.__loader = unittest.TestLoader()

    def load_i8tests(self, filename):
        name = os.path.splitext(os.path.basename(filename))[0]
        module = load_module_from_source(name, filename)
        for name in dir(module):
            item = getattr(module, name)
            if (item is not TestCase
                and type(item) is type
                and issubclass(item, TestCase)):
                self.addTest(self.__loader.loadTestsFromTestCase(item))

class ContextPopulator(object):
    def __init__(self):
        self.coverage = coverage.Accumulator()
        self.providers = []
        self.tracelevel = 0

    def import_notes(self, filename):
        self.providers.append(filename)

    def populate(self, ctx):
        ctx.coverage = self.coverage
        ctx.tracelevel = self.tracelevel
        for provider in self.providers:
            ctx.import_notes(provider)

def main(args):
    clue = "Try ‘i8x --help’ for more information."
    try:
        opts, args = getopt.gnu_getopt(
            args,
            "i:I:qt",
            ("help", "version", "import=", "quick", "trace"))
    except getopt.GetoptError as e:
        raise I8XError("%s\n%s" % (e, clue))
    ctxp = ContextPopulator()
    quickmode = False
    for opt, arg in opts:
        if opt == "--help":
            fprint(sys.stdout, USAGE)
            return
        elif opt == "--version":
            fprint(sys.stdout, cmdline.version_message_for("I8X", LICENSE))
            return
        elif opt == "-I":
            TestCase.include_path.append(arg)
        elif opt in ("-i", "--import"):
            ctxp.import_notes(arg)
        elif opt in ("-q", "--quick"):
            quickmode = True
        elif opt in ("-t", "--trace"):
            ctxp.tracelevel += 1

    if len(args) < 1:
        raise I8XError("nothing to do!\n%s" % clue)

    if quickmode:
        ctx = Context()
        try:
            ctxp.populate(ctx)
            function = args.pop(0)
            args = [strtoint_c(arg, I8XError) for arg in args]
            result = map(str, ctx.call(function, *args))
            fprint(sys.stdout, ", ".join(result))
        finally:
            ctx.finalize()
            return

    if not hasattr(TestCase, "assertIsInstance"):
        msg = ("unittest2 is required to run testcases"
               + " with Python %s.%s" % sys.version_info[:2])
        clue = module_install_command("unittest2")
        if clue is not None:
            msg += "\nTry ‘%s’" % clue
        raise I8XError(msg)

    print("I8X", version(), "on Python", sys.version)
    print("with", Context.INTERPRETER)
    print()

    TestCase._TestCase__ctxp = ctxp

    tests = TestSuite()
    for filename in args:
        tests.load_i8tests(filename)

    result = unittest.TextTestRunner(stream=sys.stdout,
                                     verbosity=2).run(tests)
    if not result.wasSuccessful():
        return 1

    if ctxp.coverage.is_total:
        return

    report = ctxp.coverage.report
    rowfmt = "%%-%ds %%3.0f%%%%" % max(map(len, report.keys()))

    print()
    if hasattr(result, "separator2"):
        print(result.separator2)
    print("Coverage:")
    print()

    for sig, counts in sorted(report.items()):
        hit, missed = counts
        print(rowfmt % (sig, 100 * hit / (hit + missed)))

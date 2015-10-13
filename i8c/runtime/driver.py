# -*- coding: utf-8 -*-
from .. import cmdline
from . import context
from . import I8XError
from . import TestCase
import getopt
import imp
import os
import subprocess
import tempfile
try:
    import unittest2 as unittest
except ImportError: # pragma: no cover
    import unittest

USAGE = u"""\
Usage: i8x [OPTION]... TESTCASE...
   or: i8x [OPTION]... [-q|--quick] FUNCTION [ARG]...

GNU Infinity note execution environment.

Options:
  --help                Display this information.
  --version             Display version information.
  -I DIR                Add the directory DIR to the list of directories
                        that TestCase.import_constants_from will search
                        for header files.
  -i, --import=ELFFILE  Import notes from ELFFILE.
  -q, --quick=FUNCTION  Execute FUNCTION with arguments from the command line.
  -t, --trace           Trace function execution.  This option may be
                        specified multiple times for greater detail.""" \
    + cmdline.usage_message_footer()

class TestSuite(unittest.TestSuite):
    def __init__(self, *args, **kwargs):
        unittest.TestSuite.__init__(self, *args, **kwargs)
        self.__loader = unittest.TestLoader()
        self.__tmpdir = tempfile.mkdtemp()

    def __del__(self):
        subprocess.call(("rm", "-rf", self.__tmpdir))

    def load_i8tests(self, ctx, filename):
        # Patch the source
        filename = self.__patch_source(filename)
        # Load the patched source
        name = os.path.splitext(os.path.basename(filename))[0]
        module = imp.load_source(name, filename)
        # Add all the tests
        for name in dir(module):
            item = getattr(module, name)
            if (item is not TestCase
                and type(item) is type
                and issubclass(item, TestCase)):
                self.addTest(self.__loader.loadTestsFromTestCase(item))

    def __patch_source(self, filename):
        # Patch the code.  We replace one line with one line
        # to preserve line numbers in exception reports.
        lines = open(filename).readlines()
        for index, line in zip(xrange(len(lines)), lines):
            if not line.lstrip().startswith("TestCase.import_"):
                continue
            line = line.replace("TestCase.", "TestCase.i8ctx.", 1)
            sub = "(globals(), %s" % repr(filename)
            line = line.replace("(", sub + ", ", 1)
            line = line.replace(sub + ", )", sub + ")")
            lines[index] = line
        # Write the patched file with the same basename, so
        # the file part is right in exceptions even if the
        # absolute pathname is different.
        name = os.path.splitext(os.path.basename(filename))[0]
        filename = os.path.join(self.__tmpdir, name + ".py")
        open(filename, "w").write("".join(lines))
        return filename

def main(args):
    try:
        opts, args = getopt.gnu_getopt(
            args,
            "i:I:qt",
            ("help", "version", "import=", "quick", "trace"))
    except getopt.GetoptError as e:
        raise I8XError(unicode(e)
                       + u"\nTry ‘i8x --help’ for more information.")
    ctx = context.Context()
    quickmode = False
    for opt, arg in opts:
        if opt == "--help":
            print USAGE
            return
        elif opt == "--version":
            print cmdline.version_message_for("i8x")
            return
        elif opt == "-I":
            ctx.include_path.append(arg)
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
        print ", ".join(map(str, ctx.call(function, *args)))
        return

    TestCase.i8ctx = ctx

    tests = TestSuite()
    for filename in args:
        tests.load_i8tests(ctx, filename)

    unittest.TextTestRunner().run(tests)

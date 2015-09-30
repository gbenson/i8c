from i8c.compiler import main
from i8c.exceptions import I8CError
from i8c.tests import TestCase
import os
import subprocess
import tempfile

SOURCE = """\
define test::func
    return
"""

class TestCompilerDriver(TestCase):
    """Test all specifiable permutations of (with_cpp,with_i8c,with_asm)."""

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.filebase = os.path.join(self.workdir, "test")
        self.infile = self.filebase + ".i8"
        open(self.infile, "w").write(SOURCE)

    def tearDown(self):
        subprocess.call(("rm", "-rf", self.workdir))

    def __run_test(self, args, outext):
        self.outfile = self.filebase + outext
        if outext != ".o":
            args.extend(("-o", self.outfile))
        args.append(self.infile)
        self.assertFalse(os.path.exists(self.outfile))
        main(args)
        self.assertTrue(os.path.isfile(self.outfile))

    def test_do_nothing(self):
        """Check that -E -fpreprocessed is rejected."""
        self.assertRaises(I8CError, main, ["-E", "-fpreprocessed"])

    def test_pp_to_asm(self):
        """Check that preprocessed source to assembly works."""
        self.__run_test(["-S", "-fpreprocessed"], ".S")

    def test_pp_to_obj(self):
        """Check that preprocessed source to object code works."""
        self.__run_test(["-fpreprocessed", "-c"], ".o")

    def test_i8_to_pp(self):
        """Check that i8 source to preprocessed source works."""
        self.__run_test(["-E"], ".i8p")

    def test_i8_to_asm(self):
        """Check that i8 source to assembly works."""
        self.__run_test(["-S"], ".S")

    def test_i8_to_obj(self):
        """Check that i8 source to object code works."""
        self.__run_test(["-c"], ".o")

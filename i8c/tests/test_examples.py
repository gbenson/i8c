from i8c.tests import TestCase
from i8c import compiler
from i8c import runtime
import os
import sys

class TestExamples(TestCase):
    def setUp(self):
        # Locate the directories
        self.__examples = os.path.join(self.topdir, "examples")
        self.__output = os.path.join(self.topdir, "tests.out",
                                     "test_examples")
        if not os.path.exists(self.__output):
            os.makedirs(self.__output)
        # Create a list of files to delete
        self.__unlink_me = []
        # Save whatever sys.argv is
        self.__saved_argv = sys.argv
        # Pipe stderr to a file
        self.__stderr = os.path.join(self.__output, "stderr")
        if os.path.exists(self.__stderr):
            os.unlink(self.__stderr)
        self.__stderr_fd = os.open(self.__stderr,
                                   os.O_RDWR | os.O_CREAT | os.O_EXCL,
                                   0600)
        sys.stderr.flush()
        self.__saved_stderr_fd = os.dup(2)
        os.dup2(self.__stderr_fd, 2)

    def tearDown(self):
        # Restore stderr
        sys.stderr.flush()
        os.dup2(self.__saved_stderr_fd, 2)
        os.close(self.__saved_stderr_fd)
        os.close(self.__stderr_fd)
        # Restore sys.argv
        sys.argv = self.__saved_argv
        # Delete anything we created in funny places
        for filename in self.__unlink_me:
            if os.path.exists(filename):
                os.unlink(filename)

    def test_factorial(self):
        """Test that the factorial example works."""
        factdir = os.path.join(self.__examples, "factorial")

        source = os.path.join(factdir, "factorial.i8")
        objfile = os.path.join(factdir, "factorial.o")
        testfile = os.path.join(factdir, "test-factorial.py")

        self.__unlink_me.append(objfile)

        # Run the exact commands in the documentation
        # XXX which is unwritten
        sys.argv[1:] = ["-c", source]
        self.assertIs(compiler.main(), None)
        sys.argv[1:] = ["-i", objfile, testfile]
        self.assertIs(runtime.main(), None)

        sys.stderr.flush()
        output = open(self.__stderr).read()
        self.assertTrue(output.endswith("\nOK\n"))
        self.assertGreaterEqual(output.find("\nRan 1 test in "), 0)

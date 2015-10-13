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
        # Pipe stdout and stderr to files
        self.__streams = {}
        for name in "stdout", "stderr":
            stream = getattr(sys, name)
            if not hasattr(stream, "fileno"):
                # Already captured by nosetests?
                continue

            fileno = stream.fileno()
            outfile = os.path.join(self.__output, name)
            if os.path.exists(outfile):
                os.unlink(outfile)
            new_fd = os.open(outfile,
                             os.O_RDWR | os.O_CREAT | os.O_EXCL,
                             0600)
            stream.flush()
            saved_fd = os.dup(fileno)
            os.dup2(new_fd, fileno)

            self.__streams[name] = outfile, stream, saved_fd, new_fd

    def tearDown(self):
        # Restore stdout and stderr
        for outfile, stream, saved_fd, new_fd in self.__streams.values():
            stream.flush()
            os.dup2(saved_fd, stream.fileno())
            os.close(saved_fd)
            os.close(new_fd)
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
        sys.argv[1:] = ["-c", source]
        self.assertIs(compiler.main(), None)
        sys.argv[1:] = ["-i", objfile, "-q", "example::factorial(i)i", "12"]
        self.assertIs(runtime.main(), None)
        sys.argv[1:] = ["-i", objfile, testfile]
        self.assertIs(runtime.main(), None)

        if hasattr(sys.stdout, "getvalue"):
            # Captured by nosetests
            output = sys.stdout.getvalue()
        else:
            # Captured by us
            sys.stdout.flush()
            output = open(self.__streams["stdout"][0]).read()
        self.assertEqual(output, "479001600\n")

        sys.stderr.flush()
        output = open(self.__streams["stderr"][0]).read()
        self.assertGreaterEqual(output.find("\nRan 1 test in "), 0)
        self.assertTrue(output.endswith("\nOK\n"))

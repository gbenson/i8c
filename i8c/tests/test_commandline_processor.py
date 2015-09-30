from i8c.compiler import CommandLine
from i8c.exceptions import I8CError
from i8c.logger import loggers
from i8c.tests import TestCase

class TestCommandLineProcessor(TestCase):
    """Tests for the command line processor."""

    def __process_command(self, cmd):
        return CommandLine(cmd.split())

    def test_empty(self):
        """Check with no arguments."""
        self.__check_empty(self.__process_command(""))

    def __check_empty(self, args):
        self.assertIs(args.showinfo, None)
        self.assertTrue(args.with_cpp)
        self.assertTrue(args.with_i8c)
        self.assertTrue(args.with_asm)
        self.assertEqual(args.infiles, [])
        self.assertIs(args.outfile, None)
        self.assertEqual(args.cpp_args, [])
        self.assertEqual(args.asm_args, [])

    def test_help(self):
        """Check that --help works."""
        for cmd in ("--help",
                    "--help --version",
                    "-O3 -E --help"):
            args = self.__process_command(cmd)
            self.assertIsNot(args.showinfo, None)
            self.assertGreaterEqual(
                args.showinfo.lower().find("usage:"), 0)

    def test_version(self):
        """Check that --version works."""
        for cmd in ("--version",
                    "--version --help",
                    "-O3 -E --version"):
            args = self.__process_command(cmd)
            self.assertIsNot(args.showinfo, None)
            self.assertGreaterEqual(
                args.showinfo.lower().find("no warranty"), 0)

    def test_E(self):
        """Check that -E works."""
        for cmd in ("-E",
                    "test.i8 -E -o test.i8i",
                    "-o test.o -S -E -fpreprocessed"):
            args = self.__process_command(cmd)
            self.assertIs(args.showinfo, None)
            self.assertFalse(args.with_i8c)
            self.assertFalse(args.with_asm)
            self.assertNotIn("-E", args.infiles)
            self.assertNotEqual(args.outfile, "-E")
            self.assertNotIn("-E", args.cpp_args)
            self.assertNotIn("-E", args.asm_args)

    def test_S(self):
        """Check that -S works."""
        for cmd in ("-S",
                    "test.i8 -S -o test.S",
                    "-o test.o -S -E -fpreprocessed"):
            args = self.__process_command(cmd)
            self.assertIs(args.showinfo, None)
            self.assertFalse(args.with_asm)
            self.assertNotIn("-S", args.infiles)
            self.assertNotEqual(args.outfile, "-S")
            self.assertNotIn("-S", args.cpp_args)
            self.assertNotIn("-S", args.asm_args)

    def test_c(self):
        """Check that -c works."""
        for cmd in ("-c",
                    "-c test.i8 -o test.S",
                    "test.i8 -c -o test.S",
                    "-o test.o -S -E -c -fpreprocessed"):
            args = self.__process_command(cmd)
            self.assertIs(args.showinfo, None)
            self.assertNotIn("-c", args.infiles)
            self.assertNotEqual(args.outfile, "-c")
            self.assertNotIn("-c", args.cpp_args)
            self.assertIn("-c", args.asm_args)

    def test_fpreprocessed(self):
        """Check that -fpreprocessed works."""
        for cmd in ("-fpreprocessed",
                    "-fpreprocessed test.i8 -o test.S",
                    "test.i8 -fpreprocessed -o test.S",
                    "-o test.o -S -E -c -fpreprocessed"):
            args = self.__process_command(cmd)
            self.assertIs(args.showinfo, None)
            self.assertFalse(args.with_cpp)
            self.assertNotIn("-fpreprocessed", args.infiles)
            self.assertNotEqual(args.outfile, "-fpreprocessed")
            self.assertNotIn("-fpreprocessed", args.cpp_args)
            self.assertNotIn("-fpreprocessed", args.asm_args)

    def test_o(self):
        """Check that -o works."""
        commands = ["-o",
                    "-fpreprocessed test.i8 -o",
                    "test.i8 -fpreprocessed -o"]
        for cmd in commands:
            self.assertRaises(I8CError, self.__process_command, cmd)

        cmd = "-o -S -E -c -fpreprocessed"
        args = self.__process_command(cmd)
        self.assertIs(args.showinfo, None)
        self.assertEqual(len(args.infiles), 0)
        self.assertEqual(args.outfile, "-S")
        self.assertNotIn("-o", args.cpp_args)
        self.assertNotIn("-S", args.cpp_args)
        self.assertIn("-o", args.asm_args)
        self.assertIn("-S", args.asm_args)

        commands.append(cmd)
        commands = [cmd.replace("-o", "-otest.o") for cmd in commands]
        self.__test_o(commands, "-otest.o")
        commands = [cmd.replace("-otest.o", "-o test.o") for cmd in commands]
        self.__test_o(commands, "-o", "test.o")

    def __test_o(self, commands, *expect):
        for cmd in commands:
            args = self.__process_command(cmd)
            self.assertIs(args.showinfo, None)
            self.assertEqual(args.outfile, "test.o")
            for arg in expect:
                self.assertNotIn(arg, args.cpp_args)
                self.assertIn(arg, args.asm_args)

    def test_x(self):
        """Check that -x is blocked."""
        commands = ("-x",
                    "-fpreprocessed -x",
                    "-x -fpreprocessed",
                    "-fpreprocessed test.i8 -x -o test.S",
                    "test.i8 -fpreprocessed -o test.S -x",
                    "-o test.o -S -E -x -c -fpreprocessed")
        self.__test_x(commands)
        commands = [cmd.replace("-x", "-xc") for cmd in commands]
        self.__test_x(commands)
        commands = [cmd.replace("-xc", "-x c") for cmd in commands]
        self.__test_x(commands)

    def __test_x(self, commands):
        for cmd in commands:
            self.assertRaises(I8CError, self.__process_command, cmd)

    def test_debug(self):
        """Check that --debug works."""
        try:
            for logger in loggers.values():
                self.assertFalse(logger.enabled)

            args = self.__process_command("")
            self.__check_empty(args)
            for logger in loggers.values():
                self.assertFalse(logger.enabled)

            args = self.__process_command("--debug=serializer")
            self.__check_empty(args)
            for name, logger in loggers.items():
                if name == "serializer":
                    self.assertTrue(logger.enabled)
                else:
                    self.assertFalse(logger.enabled)

            args = self.__process_command("--debug")
            self.__check_empty(args)
            for logger in loggers.values():
                self.assertTrue(logger.enabled)
        finally:
            for logger in loggers.values():
                logger.disable()

    def test_include(self):
        """Check that -include works."""
        for cmd in ("-include test.i8",
                    "-c -include test.i8",
                    "-include test.i8 -c"):
            args = self.__process_command(cmd)
            self.assertIn("test.i8", args.infiles)
            self.assertNotEqual(args.outfile, "test.i8")
            for arg in ("-include", "test.i8"):
                self.assertIn(arg, args.cpp_args)
                self.assertNotIn(arg, args.asm_args)

    def test_input_files(self):
        """Check that input files are handled correctly."""
        for cmd in ("test.i8",
                    "-fpreprocessed test.i8",
                    "test.i8 -fpreprocessed",
                    "-fpreprocessed -o test.S test.i8",
                    "test.i8 -fpreprocessed -o test.S",
                    "-o test.o -S -E -c  test.i8 -fpreprocessed"):
            args = self.__process_command(cmd)
            self.assertIn("test.i8", args.infiles)
            self.assertNotEqual(args.outfile, "test.i8")
            self.assertIn("test.i8", args.cpp_args)
            self.assertNotIn("test.i8", args.asm_args)

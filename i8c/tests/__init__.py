from i8c import compiler
from i8c import runtime
import os
import StringIO as stringio
import subprocess
try:
    import unittest2 as unittest
except ImportError:
    import unittest

class SourceReader(stringio.StringIO):
    def readline(self):
        line = stringio.StringIO.readline(self)
        trim = line.find("//")
        if trim >= 0:
            line = line[:trim] + "\n"
        return line

class TestOutput(runtime.Context):
    def __init__(self, testcase, index, asm):
        runtime.Context.__init__(self)
        self.__set_fileprefix(testcase, index)
        # Store the assembly language we generated
        asmfile = self.fileprefix + ".S"
        open(asmfile, "w").write(asm)
        # Assemble it
        objfile = self.fileprefix + ".o"
        subprocess.check_call(["gcc", "-c", asmfile, "-o", objfile])
        # Load the notes from it
        self.import_notes(objfile)
        self.notes = []
        for notes in self.functions.values():
            self.notes.extend(notes)
        # Make sure we got at least one note
        testcase.assertGreaterEqual(len(self.notes), 1)

    def __set_fileprefix(self, testcase, index):
        test_id = testcase.id().split(".")
        # Remove the common prefix
        for expect in "i8c", "tests":
            actual = test_id.pop(0)
            assert actual == expect
        # Remove the name of the class
        test_id.pop(-2)
        # Build the result
        index = "_%04d" % index
        self.fileprefix = os.path.join("tests.out", *test_id) + index
        # Ensure the directory we'll write to exists
        dir = os.path.dirname(self.fileprefix)
        if not os.path.exists(dir):
            os.makedirs(dir)

    @property
    def note(self):
        assert len(self.notes) == 1
        return self.notes[0]

    @property
    def ops(self):
        ops = self.note.ops.items()
        ops.sort()
        return [op for pc, op in ops]

    @property
    def opnames(self):
        return [op.name for op in self.ops]

class TestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.compilecount = 0

    def compile(self, input):
        self.compilecount += 1
        input = SourceReader('# 1 "<testcase>"\n' + input)
        output = stringio.StringIO()
        tree = compiler.compile(input.readline, output.write)
        return tree, TestOutput(self, self.compilecount, output.getvalue())

    def disable_loggers(self):
        for logger in compiler.loggers.values():
            logger.disable()

    def collect_blocks(self, function):
        result = {}
        self.__collect_blocks(result, function.entry_block)
        return result

    def __collect_blocks(self, result, block):
        if not result.has_key(block.index):
            result[block.index] = block
            for block in block.exits:
                self.__collect_blocks(result, block)

from i8c import compiler
import os
import StringIO as stringio
import subprocess
import unittest

class Reader(stringio.StringIO):
    def readline(self):
        line = stringio.StringIO.readline(self)
        trim = line.find("//")
        if trim >= 0:
            line = line[:trim] + "\n"
        return line

class Output(object):
    def __init__(self, test_id, asm):
        self.__set_fileprefix(test_id)
        self.asm = asm
        asmfile = self.fileprefix + ".S"
        open(asmfile, "w").write(asm)
        objfile = self.fileprefix + ".o"
        subprocess.check_call(["gcc", "-c", asmfile, "-o", objfile])

    def __set_fileprefix(self, test_id):
        test_id = test_id.split(".")
        # Remove the common prefix
        for expect in "i8c", "tests":
            actual = test_id.pop(0)
            assert actual == expect
        # Remove the name of the class
        test_id.pop(-2)
        self.fileprefix = os.path.join("tests.out", *test_id)
        # Ensure the directory we'll write to exists
        dir = os.path.dirname(self.fileprefix)
        if not os.path.exists(dir):
            os.makedirs(dir)

    @property
    def operations(self):
        return [part.split(None, 1)[0]
                for part in self.asm.split("\t.byte DW_OP_")[1:]]

class TestCase(unittest.TestCase):
    def compile(self, input):
        input = Reader('# 1 "<testcase>"\n' + input)
        output = stringio.StringIO()
        tree = compiler.compile(input.readline, output.write)
        return tree, Output(self.id(), output.getvalue())

from i8c import compiler
from i8c import emitter
from i8c.logger import loggers
import os
import StringIO as stringio
import struct
import subprocess
try:
    import unittest2 as unittest
except ImportError:
    import unittest

class TestError(Exception):
    pass

class Reader(stringio.StringIO):
    def readline(self):
        line = stringio.StringIO.readline(self)
        trim = line.find("//")
        if trim >= 0:
            line = line[:trim] + "\n"
        return line

class Output(object):
    def __init__(self, test_id, index, asm):
        self.__set_fileprefix(test_id, index)
        self.asm = asm
        asmfile = self.fileprefix + ".S"
        open(asmfile, "w").write(asm)
        objfile = self.fileprefix + ".o"
        subprocess.check_call(["gcc", "-c", asmfile, "-o", objfile])
        self.__extract_note(objfile)

    def __set_fileprefix(self, test_id, index):
        test_id = test_id.split(".")
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

    def __extract_note(self, objfile):
        objfile = open(objfile).read()
        for self.byteorder in "<>":
            search = struct.pack(self.byteorder + "I4sH",
                                 emitter.NT_GNU_INFINITY,
                                 "GNU\0",
                                 emitter.I8_FUNCTION_MAGIC)
            index = objfile.find(search)
            if index < 0:
                continue
            if objfile.find(search, index + 1) > index:
                raise TestError("multiple notes found")
            index -= 8 # backtrack to get namesz and descsz
            [namesz, descsz] = struct.unpack(self.byteorder + "2I",
                                             objfile[index: index + 8])
            self.note = objfile[index:index + 12 + namesz + descsz]
            break
        else:
            raise TestError("note not found")

    @property
    def operations(self):
        return [part.split(None, 1)[0]
                for part in self.asm.split("\t.byte DW_OP_")[1:]]

class TestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.compilecount = 0

    def compile(self, input):
        self.compilecount += 1
        input = Reader('# 1 "<testcase>"\n' + input)
        output = stringio.StringIO()
        tree = compiler.compile(input.readline, output.write)
        return tree, Output(self.id(), self.compilecount, output.getvalue())

    def disable_loggers(self):
        for logger in loggers.values():
            logger.disable()

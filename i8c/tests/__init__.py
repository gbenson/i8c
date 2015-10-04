from i8c import compiler
from i8c import dwarf2
from i8c import constants
from i8c.logger import loggers
import os
import StringIO as stringio
import struct
import subprocess
try:
    import unittest2 as unittest
except ImportError:
    import unittest

class Reader(stringio.StringIO):
    def readline(self):
        line = stringio.StringIO.readline(self)
        trim = line.find("//")
        if trim >= 0:
            line = line[:trim] + "\n"
        return line

class Output(object):
    def __init__(self, testcase, index, asm):
        self.__set_fileprefix(testcase, index)
        self.asm = asm
        asmfile = self.fileprefix + ".S"
        open(asmfile, "w").write(asm)
        objfile = self.fileprefix + ".o"
        subprocess.check_call(["gcc", "-c", asmfile, "-o", objfile])
        self.note = self.__extract_note(testcase, objfile)

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

    def __extract_note(self, testcase, objfile):
        objfile = open(objfile).read()
        for byteorder in "<>":
            search = struct.pack(byteorder + "I4sH",
                                 constants.NT_GNU_INFINITY,
                                 "GNU\0",
                                 constants.I8_FUNCTION_MAGIC)
            index = objfile.find(search)
            if index < 0:
                continue
            if objfile.find(search, index + 1) > index:
                testcase.fail("multiple notes found")
            index -= 8 # backtrack to get namesz and descsz
            [namesz, descsz] = struct.unpack(byteorder + "2I",
                                             objfile[index: index + 8])
            testcase.assertEqual(namesz, 4)
            descstart = index + 12 + namesz
            desclimit = descstart + descsz
            return Note(testcase, byteorder, objfile[descstart:desclimit])
        testcase.fail("note not found")

    @property
    def ops(self):
        return self.note.ops

    @property
    def opnames(self):
        return [op.name for op in self.ops]

class Note(object):
    def __init__(self, testcase, byteorder, data):
        # Parse the header
        hdrformat = byteorder + "11H"
        expect_hdrsize = struct.calcsize(hdrformat)
        (magic, version, hdrsize, codesize, externsize, prov_o, name_o,
         ptypes_o, rtypes_o, etypes_o, self.max_stack) = struct.unpack(
            hdrformat, data[:expect_hdrsize])

        # Check the header
        testcase.assertEqual(magic, constants.I8_FUNCTION_MAGIC)
        testcase.assertEqual(version, 1)
        testcase.assertEqual(hdrsize, expect_hdrsize - 4)

        codestart = 4 + hdrsize
        externstart = codestart + codesize
        stringstart = externstart + externsize

        # Extract the strings
        strings = data[stringstart:]
        (self.provider, self.name, self.ptypes, self.rtypes,
         self.etypes) = (self.__getstring(testcase, strings, start)
                         for start in (prov_o, name_o, ptypes_o,
                                       rtypes_o, etypes_o))

        # Disassemble the bytecode
        self.__disassemble(testcase, byteorder, data[codestart:externstart])

    def __getstring(self, testcase, strings, start):
        limit = strings.find("\0", start)
        testcase.assertGreaterEqual(limit, start)
        return strings[start:limit]

    def __disassemble(self, testcase, byteorder, code):
        self.ops, pc = [], 0
        while pc < len(code):
            op = Operation.from_code(testcase, byteorder, code, pc)
            self.ops.append(op)
            pc += op.size

class Operation(object):
    @classmethod
    def from_code(cls, testcase, byteorder, code, pc):
        dwop = dwarf2.by_opcode[ord(code[pc])]
        size, operands = cls.decode_operands(
            dwop, testcase, byteorder, code, pc + 1)
        return cls(dwop.name[len("DW_OP_"):], size + 1, operands)

    @classmethod
    def decode_operands(cls, dwop, *args):
        if dwop.operands is None:
            return 0, ()
        for c in dwop.operands:
            if ord(c) < ord(" "):
                return cls.decode_special(dwop, *args)
        else:
            return cls.decode_simple(dwop, *args)

    @staticmethod
    def decode_simple(dwop, testcase, byteorder, code, start):
        format = byteorder + dwop.operands
        size = struct.calcsize(format)
        return size, struct.unpack(format, code[start:start + size])

    @classmethod
    def decode_special(cls, dwop, testcase, byteorder, code, start):
        if len(dwop.operands) > 1:
            raise NotImplementedError
        type = dwop.operands[0]
        if type == dwarf2.DwOp.OP_ULEB:
            is_signed = False
        elif type == dwarf2.DwOp.OP_SLEB:
            is_signed = True
        else:
            raise NotImplementedError
        size, value = cls.decode_leb128(code, start, is_signed)
        return size, (value,)

    @staticmethod
    def decode_leb128(code, start, is_signed):
        result = shift = 0
        offset = start
        while True:
            byte = ord(code[offset])
            offset += 1
            result |= ((byte & 0x7f) << shift)
            if (byte & 0x80) == 0:
                break
            shift += 7
        if is_signed and (byte & 0x40):
            sign = 0x40 << shift
            result &= ~(0x40 << shift)
            result -= sign
        return offset - start, result

    def __init__(self, name, size, operands):
        self.name = name
        self.size = size
        self.operands = operands

    @property
    def operand(self):
        assert len(self.operands) == 1
        return self.operands[0]

class TestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.compilecount = 0

    def compile(self, input):
        self.compilecount += 1
        input = Reader('# 1 "<testcase>"\n' + input)
        output = stringio.StringIO()
        tree = compiler.compile(input.readline, output.write)
        return tree, Output(self, self.compilecount, output.getvalue())

    def disable_loggers(self):
        for logger in loggers.values():
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

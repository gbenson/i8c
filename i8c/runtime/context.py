from .. import constants
from . import ELFError, CorruptNoteError, UnhandledNoteError
from . import operations
import struct

class Context(object):
    def __init__(self):
        self.functions = {}

    def register_function(self, function):
        funclist = self.functions.get(function.name, [])
        if not funclist:
            self.functions[function.name] = funclist
        funclist.append(function)

    def import_notes(self, filename):
        with open(filename) as fp:
            fmt = "4sxB"
            data = fp.read(struct.calcsize(fmt))
            magic, byteorder = struct.unpack(fmt, data)
            if magic != "\x7fELF":
                raise ELFError(filename, "not an ELF file")
            byteorder = {1: "<", 2: ">"}[byteorder]
            data = fp.read()
        name = "GNU\0"
        hfmt, mfmt = byteorder + "2I", byteorder + "I4sH"
        marker = struct.pack(mfmt, constants.NT_GNU_INFINITY,
                             name, constants.I8_FUNCTION_MAGIC)
        start = hdrsz = struct.calcsize(hfmt)
        while True:
            start = data.find(marker, start)
            if start < 0:
                break
            start -= hdrsz
            namesz, descsz = struct.unpack(hfmt,
                                           data[start:start + hdrsz])
            if namesz != len(name):
                raise ELFError(filename, "corrupt note about 0x%x", index)
            descstart = start + hdrsz + struct.calcsize("I") + len(name)
            desclimit = descstart + descsz
            self.register_function(Function((filename, descstart),
                                            data[descstart:desclimit],
                                            byteorder))
            start = desclimit

class Function(object):
    def __init__(self, location, data, byteorder):
        self.location = location

        # Parse the header
        hdrformat = byteorder + "11H"
        expect_hdrsize = struct.calcsize(hdrformat)
        (magic, version, hdrsize, codesize, externsize, prov_o, name_o,
         ptypes_o, rtypes_o, etypes_o, self.max_stack) = struct.unpack(
            hdrformat, data[:expect_hdrsize])

        # Check the header
        if magic != constants.I8_FUNCTION_MAGIC:
            if magic >> 8 == magic & 0xFF:
                raise CorruptNoteError(self)
            else:
                raise UnhandledNoteError(self)
        if version != 1:
            raise UnhandledNoteError(self)
        if hdrsize != expect_hdrsize - 4:
            raise CorruptNoteError(self)

        # Work out where everything is
        codestart = 4 + hdrsize
        externstart = codestart + codesize
        stringstart = externstart + externsize

        # Extract the strings
        strings = data[stringstart:]
        (self.provider, self.shortname, self.ptypes, self.rtypes,
         self.etypes) = (self.__get_string(strings, start)
                         for start in (prov_o, name_o, ptypes_o,
                                       rtypes_o, etypes_o))
        self.name = "%s::%s(%s)%s" % (self.provider, self.shortname,
                                      self.ptypes, self.rtypes)

        # Decode the bytecode
        self.__decode_ops(data[codestart:externstart], byteorder)

    def __get_string(self, strings, start):
        limit = strings.find("\0", start)
        if limit < start:
            raise CorruptNoteError(self)
        return strings[start:limit]

    def __decode_ops(self, code, byteorder):
        self.ops, pc = [], 0
        while pc < len(code):
            op = operations.Operation((self.name, pc), code, byteorder)
            self.ops.append(op)
            pc += op.size

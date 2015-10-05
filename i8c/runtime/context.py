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
        self.byteorder = byteorder

        # Parse the header
        hdrformat = byteorder + "11H"
        expect_hdrsize = struct.calcsize(hdrformat)
        (magic, version, hdrsize, codesize, externsize, provider_o, name_o,
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
        self.strings = data[stringstart:]
        (provider, name, ptypes, rtypes, etypes) = map(self.get_string,
                       (provider_o, name_o, ptypes_o, rtypes_o, etypes_o))
        self.name = "%s::%s(%s)%s" % (provider, name, ptypes, rtypes)

        # Load the bytecode and externals
        self.__load_bytecode(data[codestart:externstart])
        self.__load_externals(etypes, data[externstart:stringstart])

    def get_string(self, start):
        limit = self.strings.find("\0", start)
        if limit < start:
            raise CorruptNoteError(self)
        return self.strings[start:limit]

    def __load_bytecode(self, code):
        self.ops, pc = [], 0
        while pc < len(code):
            op = operations.Operation((self.name, pc), code, self.byteorder)
            self.ops.append(op)
            pc += op.size

    def __load_externals(self, etypes, data):
        self.externals = []
        if not etypes:
            return
        slotsize, check = divmod(len(data), len(etypes))
        if check != 0:
            raise CorruptNoteError(self)
        for type, index in zip(etypes, range(len(etypes))):
            klass = {"f": FuncRefExternal,
                     "x": RelAddrExternal}.get(type, None)
            if klass is None:
                raise UnhandledNoteError(self)
            start = index * slotsize
            limit = start + slotsize
            self.externals.append(klass(self, data[start:limit]))

class External(object):
    @property
    def is_function(self):
        return isinstance(self, FuncRefExternal)

    @property
    def is_unrelocated_address(self):
        return isinstance(self, RelAddrExternal)

class FuncRefExternal(External):
    def __init__(self, note, data):
        format = note.byteorder + "4H"
        slotsize = struct.calcsize(format)
        self.name = "%s::%s(%s)%s" % tuple(map(
            note.get_string, struct.unpack(format, data[:slotsize])))

class RelAddrExternal(External):
    def __init__(self, note, data):
        format = {4: "I", 8: "Q"}.get(len(data), None)
        if format is None:
            raise UnhandledNoteError(note)
        format = note.byteorder + format
        self.value = struct.unpack(format, data)[0]

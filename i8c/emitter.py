from i8c import logger
from i8c import dwarf2
import copy

debug_print = logger.debug_printer_for(__name__)

NT_GNU_INFINITY = 5
I8_FUNCTION_MAGIC = (ord("i") << 8) | ord("8")

class Label(object):
    def __init__(self, name):
        self.name = name
        self.emitted = False

    @property
    def ref(self):
        return self.name + (self.emitted and "b" or "f")

    def __sub__(self, other):
        if other is self:
            return "0"
        else:
            return "%s-%s" % (self.ref, other.ref)

class String(object):
    def __init__(self, table, text):
        self.text = text

    def append(self, more):
        self.text += more

class StringTable(object):
    def __init__(self):
        self.strings = []
        self.entries = []

    @property
    def is_laid_out(self):
        return len(self.entries) != 0

    @property
    def start_label(self):
        return self.entries[0][0]

    def new(self, text=""):
        assert not self.is_laid_out
        result = String(self, text)
        self.strings.append(result)
        return result

    def layout_table(self, new_label):
        assert not self.is_laid_out
        # Create a length-sorted list of unique strings
        unique = {}
        for string in self.strings:
            unique[string.text] = True
        unique = [(-len(text), text) for text in unique.keys()]
        unique.sort()
        # Calculate offsets for each
        offsets = {}
        for junk, text in unique:
            for label, entry_text in self.entries:
                if entry_text.endswith(text):
                    offsets[text] = "%s+%d" % (
                        offsets[entry_text],
                        len(entry_text) - len(text))
                    break
            else:
                label = new_label()
                self.entries.append((label, text))
                offsets[text] = label - self.start_label
        # Store the offsets in the strings
        for string in self.strings:
            string.offset = offsets[string.text]

    def emit(self, emitter):
        for label, text in self.entries:
            emitter.emit_label(label)
            emitter.emit('.string "%s"' % text)

class ExternTable(object):
    def __init__(self, strings):
        self.strings = strings
        self.entries = []

    def visit_funcref(self, funcref):
        fullname, type = funcref.name.value, funcref.typename.type
        self.entries.append(FuncRef(*map(self.strings.new, (
            fullname.provider,
            fullname.name,
            "".join((t.encoding for t in type.paramtypes)),
            "".join((t.encoding for t in type.returntypes))))))

    def visit_symref(self, symref):
        fullname = symref.name.value
        assert fullname.is_shortname
        self.entries.append(SymRef(fullname.name))

    def emit(self, emitter):
        for entry, index in zip(self.entries, xrange(len(self.entries))):
            entry.emit(emitter, "extern %d " % index)

class FuncRef(object):
    def __init__(self, provider, name, params, returns):
        self.provider = provider
        self.name = name
        self.params = params
        self.returns = returns

    def emit(self, emitter, prefix):
        emitter.emit_2byte(self.provider.offset, prefix + "provider offset")
        emitter.emit_2byte(self.name.offset, prefix + "name offset")
        emitter.emit_2byte(self.params.offset, prefix + "ptypes offset")
        emitter.emit_2byte(self.returns.offset, prefix + "rtypes offset")

class SymRef(object):
    def __init__(self, name):
        self.name = name

    def emit(self, emitter, prefix):
        emitter.emit_8byte(self.name, prefix + "address")

class Emitter(object):
    def __init__(self, write):
        self.write = write
        self.num_labels = 0
        self.__label = None
        self.opcodes = copy.copy(dwarf2.by_name)

    def new_label(self):
        self.num_labels += 1
        return Label(str(self.num_labels))

    def emit(self, line, comment=None):
        if line.startswith("."):
            line = "\t" + line
        if not line.startswith("#") and self.__label is not None:
            line = "%s:%s" % (self.__label.name, line)
            self.__label = None
        if comment is not None:
            line += "\t/* %s */" % comment
        line += "\n"
        self.write(line)

    def emit_newline(self):
        self.emit("")

    def emit_comment(self, comment):
        self.emit("", comment)

    def emit_label(self, label):
        if self.__label is not None:
            self.write("%s:\n" % self.__label.name)
            self.__label = None
        self.__label = label
        label.emitted = True

    def __emit_nbyte(self, n, value, comment):
        self.emit((".%sbyte " % n) + str(value), comment)

    def emit_byte(self, value, comment=None):
        self.__emit_nbyte("", value, comment)

    def emit_2byte(self, value, comment=None):
        self.__emit_nbyte(2, value, comment)

    def emit_4byte(self, value, comment=None):
        self.__emit_nbyte(4, value, comment)

    def emit_8byte(self, value, comment=None):
        self.__emit_nbyte(8, value, comment)

    def emit_uleb128(self, value, comment=None):
        self.emit(".uleb128 " + str(value), comment)

    def emit_sleb128(self, value, comment=None):
        self.emit(".sleb128 " + str(value), comment)

    def emit_op(self, name, comment=None):
        assert name != "addr" # See XXX UNWRITTEN DOCS.
        name = "DW_OP_" + name
        op = self.opcodes.pop(name, None)
        if op is not None:
            self.emit("#define %s 0x%02x" % (name, op.opcode))
        self.emit_byte(name, comment)

    def visit_toplevel(self, toplevel):
        self.emit("#define NT_GNU_INFINITY %d" % NT_GNU_INFINITY)
        self.emit("#define I8_FUNCTION_MAGIC 0x%x" % I8_FUNCTION_MAGIC)
        self.emit('.section .note.infinity, "", "note"')
        self.emit(".balign 4")
        for node in toplevel.functions:
            node.accept(self)

    def visit_function(self, function):
        debug_print("\n%s:\n" % function.name.value)
        # This method handles laying out the structure of the note
        # as per http://www.netbsd.org/docs/kernel/elf-notes.html.
        # The Infinity-specific part is in the "desc" field and is
        # handled by self.__visit_function.
        namestart = self.new_label()
        namelimit = self.new_label()
        descstart = self.new_label()
        desclimit = self.new_label()
        self.emit_newline()
        self.emit_comment(function.name.ident)
        self.emit_4byte(namelimit - namestart, "namesz")
        self.emit_4byte(desclimit - descstart, "descsz")
        self.emit_4byte("NT_GNU_INFINITY")
        self.emit_label(namestart)
        self.emit('.string "GNU"')
        self.emit_label(namelimit)
        self.emit(".balign 4")
        self.emit_label(descstart)
        self.__visit_function(function)
        self.emit_label(desclimit)
        self.emit(".balign 4")

    def __visit_function(self, function):
        headerstart = self.new_label()
        codestart = self.new_label()
        etablestart = self.new_label()

        strings = StringTable()
        self.externs = ExternTable(strings)

        # Populate the tables
        provider = strings.new(function.name.provider)
        name = strings.new(function.name.shortname)
        self.paramtypes = strings.new()
        self.externtypes = strings.new()
        self.returntypes = strings.new()
        for node in function.entry_stack:
            node.accept(self)
        function.returntypes.accept(self)
        strings.layout_table(self.new_label)

        # Emit the Infinity note header
        self.emit_2byte("I8_FUNCTION_MAGIC")
        self.emit_2byte(1, "version")

        # Emit the Infinity function header
        self.emit_label(headerstart)
        self.emit_2byte(codestart - headerstart, "header size")
        self.emit_2byte(etablestart - codestart, "code size")
        self.emit_2byte(strings.start_label - etablestart, "externs size")
        self.emit_2byte(provider.offset, "provider offset")
        self.emit_2byte(name.offset, "name offset")
        self.emit_2byte(self.paramtypes.offset, "param types offset")
        self.emit_2byte(self.returntypes.offset, "return types offset")
        self.emit_2byte(self.externtypes.offset, "externs types offset")
        self.emit_2byte(function.max_stack, "max stack")

        # Emit the code
        self.emit_label(codestart)
        function.ops.accept(self)

        # Emit the extern table
        self.emit_label(etablestart)
        self.externs.emit(self)

        # Emit the string table
        strings.emit(self)

    # Populate the string and extern tables

    def visit_parameters(self, parameters):
        self.__visit_parameters(parameters)

    def visit_externals(self, externals):
        self.__visit_parameters(externals)

    def __visit_parameters(self, parameters):
        for node in parameters.children:
            node.accept(self)

    def visit_parameter(self, param):
        self.paramtypes.append(param.typename.type.encoding)

    def visit_returntypes(self, returntypes):
        for node in returntypes.children:
            self.returntypes.append(node.type.encoding)

    def visit_funcref(self, funcref):
        self.externtypes.append("f")
        funcref.accept(self.externs)

    def visit_symref(self, symref):
        self.externtypes.append("x")
        symref.accept(self.externs)

    # Emit the bytecode

    def visit_operationstream(self, stream):
        debug_print("%s\n" % stream)
        self.jumps = stream.jumps
        self.labels = {}
        for op in stream.labels.keys():
            self.labels[op] = self.new_label()
        ops = stream.ops.items()
        ops.sort()
        for index, op in ops:
            label = self.labels.get(op, None)
            if label is not None:
                self.emit_label(label)
            op.accept(self)

    def emit_simple_op(self, op):
        self.emit_op(op.dwarfname, op.fileline)

    def emit_branch_op(self, op):
        target = self.labels[self.jumps[op]]
        source = self.new_label()
        self.emit_simple_op(op)
        self.emit_2byte(target - source)
        self.emit_label(source)

    visit_addop = emit_simple_op
    visit_binaryop = emit_simple_op
    visit_branchop = emit_branch_op
    visit_callop = emit_simple_op
    visit_compareop = emit_simple_op

    def visit_constop(self, op):
        value = op.value
        if value >= 0:
            if value < 0x20:
                self.emit_op("lit%d" % value, op.fileline)
            elif value < (1 << 8):
                self.emit_op("const1u", op.fileline)
                self.emit_byte(value)
            elif value < (1 << 16):
                self.emit_op("const2u", op.fileline)
                self.emit_2byte(value)
            elif value < (1 << 21):
                self.emit_op("constu", op.fileline)
                self.emit_uleb128(value)
            elif value < (1 << 32):
                self.emit_op("const4u", op.fileline)
                self.emit_4byte(value)
            elif value < (1 << 49):
                self.emit_op("constu", op.fileline)
                self.emit_uleb128(value)
            elif value < (1 << 64):
                self.emit_op("const8u", op.fileline)
                self.emit_8byte(value)
            else:
                self.emit_op("constu", op.fileline)
                self.emit_uleb128(value)
        else:
            if value >= -(1 << 7):
                self.emit_op("const1s", op.fileline)
                self.emit_byte(value)
            elif value >= -(1 << 15):
                self.emit_op("const2s", op.fileline)
                self.emit_2byte(value)
            elif value >= -(1 << 20):
                self.emit_op("consts", op.fileline)
                self.emit_sleb128(value)
            elif value >= -(1 << 31):
                self.emit_op("const4s", op.fileline)
                self.emit_4byte(value)
            elif value >= -(1 << 48):
                self.emit_op("consts", op.fileline)
                self.emit_sleb128(value)
            elif value >= -(1 << 63):
                self.emit_op("const8s", op.fileline)
                self.emit_8byte(value)
            else:
                self.emit_op("consts", op.fileline)
                self.emit_sleb128(value)

    def visit_derefop(self, op):
        sizedtype = op.type.sizedtype
        if sizedtype is None:
            self.emit_op("deref", op.fileline)
            return

        self.emit_op("deref_size", op.fileline)
        self.emit_byte(sizedtype.size_bytes)
        if not sizedtype.is_signed:
            return

        # Sign extension.
        # i.e. value = ((value << SHIFT) >>> SHIFT)
        # This code works for 32- and 64-bit machines.
        if sizedtype.size_bytes == 8:
            return
        self.emit_op("const1u", "sign extension for %s" % sizedtype.name)
        self.emit_byte(32)
        self.emit_op("dup")
        self.emit_op("dup")
        self.emit_op("shl")
        self.emit_op("swap")
        self.emit_op("shr")
        # stack[0]: 32 (on 64-bit machines) or 0 (on 32-bit)
        # stack[1]: unextended value
        shift_for_32bit = (4 - sizedtype.size_bytes) * 8
        if shift_for_32bit > 0:
            self.emit_op("plus_uconst")
            self.emit_uleb128(shift_for_32bit)
        # stack[0]: required shift for sign extension
        # stack[1]: unextended value
        self.emit_op("dup")
        self.emit_op("rot")
        self.emit_op("shl")
        self.emit_op("swap")
        self.emit_op("shra")
        self.emit_comment("End of sign extension.")

    visit_dropop = emit_simple_op
    visit_dupop = emit_simple_op
    visit_gotoop = emit_branch_op

    def visit_nameop(self, op):
        pass

    visit_overop = emit_simple_op

    def visit_pickop(self, op):
        if op.slot == 0:
            self.emit_op("dup", op.fileline)
        elif op.slot == 1:
            self.emit_op("over", op.fileline)
        else:
            self.emit_op("pick", op.fileline)
            self.emit_byte(op.slot)

    visit_rotop = emit_simple_op

    def visit_stopop(self, op):
        pass

    visit_subop = emit_simple_op
    visit_swapop = emit_simple_op
    visit_unaryop = emit_simple_op

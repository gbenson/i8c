from i8c import dwarf2

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

class AutosTable(object):
    def __init__(self, strings):
        self.strings = strings
        self.entries = []

    def string_or_None(self, text):
        if text is not None:
            return self.strings.new(text)

    def add_entry(self, fullname, args=None, rets=None):
        self.entries.append(
            map(self.string_or_None,
                (fullname.provider, fullname.name, args, rets)))

    def visit_funcref(self, funcref):
        name, type = funcref.name.value, funcref.typename.type
        self.add_entry(funcref.name.value,
                       "".join((t.encoding for t in type.paramtypes)),
                       "".join((t.encoding for t in type.returntypes)))

    def visit_symbolref(self, symref):
        self.add_entry(symref.name.value)

    def emit(self, emitter):
        for entry, index in zip(self.entries, xrange(len(self.entries))):
            prov, name, args, rets = entry
            prefix = "auto %d " % index
            emitter.emit_2byte(prov.offset, prefix + "provider offset")
            emitter.emit_2byte(name.offset, prefix + "name offset")
            if args is None:
                assert rets is None
                emitter.emit_4byte(0, prefix + "reserved bytes")
                continue
            emitter.emit_2byte(args.offset, prefix + "ptypes offset")
            emitter.emit_2byte(rets.offset, prefix + "rtypes offset")

class Emitter(object):
    def __init__(self, write):
        self.write = write
        self.num_labels = 0
        self.__label = None
        self.__init_opcodes()

    def __init_opcodes(self):
        self.opcodes = {}
        for name in dir(dwarf2):
            if name.startswith("DW_OP_"):
                self.opcodes[name] = getattr(dwarf2, name)

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

    def emit_op(self, name, comment=None):
        name = "DW_OP_" + name
        code = self.opcodes.pop(name, None)
        if code is not None:
            self.emit("#define %s 0x%02x" % (name, code))
        self.emit_byte(name, comment)

    def visit_toplevel(self, toplevel):
        self.emit("#define NT_GNU_INFINITY 5")
        self.emit("#define ELF_NOTE_I8_FUNCTION 1")
        self.emit_newline()
        self.emit('.section .note.infinity, "", "note"')
        self.emit(".balign 4")
        for node in toplevel.functions:
            node.accept(self)

    def visit_function(self, function):
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
        autosstart = self.new_label()

        strings = StringTable()
        self.autos = AutosTable(strings)

        # Populate the tables
        provider = strings.new(function.name.provider)
        name = strings.new(function.name.shortname)
        self.userptypes = strings.new()
        self.autoptypes = strings.new()
        self.returntypes = strings.new()
        for node in function.parameters:
            node.accept(self)
        function.returntypes.accept(self)
        strings.layout_table(self.new_label)

        # Emit the Infinity note header
        self.emit_2byte("ELF_NOTE_I8_FUNCTION")
        self.emit_2byte(1, "version")

        # Emit the Infinity function header
        self.emit_label(headerstart)
        self.emit_2byte(codestart - headerstart, "header size")
        self.emit_2byte(autosstart - codestart, "code size")
        self.emit_2byte(strings.start_label - autosstart, "autos size")
        self.emit_2byte(provider.offset, "provider offset")
        self.emit_2byte(name.offset, "name offset")
        self.emit_2byte(self.userptypes.offset, "param types offset")
        self.emit_2byte(self.returntypes.offset, "return types offset")
        self.emit_2byte(self.autoptypes.offset, "autos types offset")
        self.emit_2byte(function.max_stack, "max stack")

        # Emit the code
        self.emit_label(codestart)
        function.ops.accept(self)

        # Emit the automatic parameter slots
        self.emit_label(autosstart)
        self.autos.emit(self)

        # Emit the string table
        strings.emit(self)

    # Populate the string and automatic parameter tables

    def visit_userparams(self, userparams):
        self.__visit_parameters(userparams)

    def visit_autoparams(self, autoparams):
        self.__visit_parameters(autoparams)

    def __visit_parameters(self, parameters):
        for node in parameters.children:
            node.accept(self)

    def visit_parameter(self, param):
        self.userptypes.append(param.typename.type.encoding)

    def visit_returntypes(self, returntypes):
        for node in returntypes.children:
            self.returntypes.append(node.type.encoding)

    def visit_funcref(self, funcref):
        self.autoptypes.append("f")
        funcref.accept(self.autos)

    def visit_symbolref(self, symref):
        self.autoptypes.append("s")
        symref.accept(self.autos)

    # Emit the bytecode

    def visit_operationstream(self, stream):
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

    visit_branchop = emit_branch_op
    visit_callop = emit_simple_op
    visit_compareop = emit_simple_op

    def visit_constop(self, op):
        value = op.value
        if value >= 0 and value <= 31:
            self.emit_op("lit%d" % value, op.fileline)
            return
        raise NotImplementedError

    def visit_derefop(self, op):
        if op.type.sizedtype is not None:
            raise NotImplementedError
        self.emit_op("deref", op.fileline)

    visit_dropop = emit_simple_op
    visit_gotoop = emit_branch_op
    visit_rotop = emit_simple_op

    def visit_stopop(self, op):
        pass

    visit_swapop = emit_simple_op

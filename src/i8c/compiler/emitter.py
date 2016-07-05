# -*- coding: utf-8 -*-
# Copyright (C) 2015-16 Red Hat, Inc.
# This file is part of the Infinity Note Compiler.
#
# The Infinity Note Compiler is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# The Infinity Note Compiler is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Infinity Note Compiler.  If not, see
# <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from .. import archspec
from .. import constants
from ..compat import fwrite, str
from . import logger
from . import types
from . import visitors
from .types import PTRTYPE

debug_print = logger.debug_printer_for(__name__)

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

    @staticmethod
    def quote(text):
        return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"')

    @property
    def quoted(self):
        return String.quote(self.text)

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
            emitter.emit(".string " + String.quote(text))

class ExternTable(object):
    def __init__(self, funcname, strings):
        self.strings = strings
        self.indexes = {str(funcname): 0}
        self.entries = []

    def index_of(self, external):
        key = str(external.name)
        index = self.indexes.get(key, None)
        if index is not None:
            return index
        index = len(self.entries) + 1
        type = external.basetype
        assert type.is_function
        self.entries.append(FuncRef(*map(self.strings.new, (
            external.name.provider,
            external.name.name,
            "".join((t.encoding for t in type.paramtypes)),
            "".join((t.encoding for t in type.returntypes))))))
        self.indexes[key] = index
        return index

    def emit(self, emitter):
        for entry, index in zip(self.entries, range(1, len(self.entries) + 1)):
            entry.emit(emitter, "extern %d " % index)

class FuncRef(object):
    def __init__(self, provider, name, params, returns):
        self.provider = provider
        self.name = name
        self.params = params
        self.returns = returns

    def emit(self, emitter, prefix):
        emitter.emit_uleb128(self.provider.offset, prefix + "provider offset")
        emitter.emit_uleb128(self.name.offset, prefix + "name offset")
        emitter.emit_uleb128(self.params.offset, prefix + "ptypes offset")
        emitter.emit_uleb128(self.returns.offset, prefix + "rtypes offset")

class TableBuilder(object):
    def __init__(self, emitter):
        self.emitter = emitter

    def visit_function(self, function):
        funcname = function.name.value
        assert funcname.is_fullname
        self.strings = StringTable()
        self.externs = ExternTable(funcname, self.strings)

        # Create strings for the signature chunk.
        self.emitter.provider = self.strings.new(funcname.provider)
        self.emitter.name = self.strings.new(funcname.name)
        self.emitter.paramtypes = self.strings.new()
        function.parameters.accept(self)
        self.emitter.returntypes = self.strings.new()
        function.returntypes.accept(self)

        # Create externals and strings for the bytecode chunk.
        function.ops.accept(self)

        # Lay out the strings table.
        self.strings.layout_table(self.emitter.new_label)

        self.emitter.strings = self.strings
        self.emitter.externs = self.externs

    def visit_parameters(self, parameters):
        for node in parameters.children:
            node.accept(self)

    def visit_parameter(self, param):
        self.emitter.paramtypes.append(param.typename.type.encoding)

    def visit_returntypes(self, returntypes):
        for node in returntypes.children:
            self.emitter.returntypes.append(node.type.encoding)

    def visit_operationstream(self, ops):
        for index, op in ops.stream:
            op.accept(self)

    def visit_loadop(self, op):
        if op.is_loadext and op.external.type.is_function:
            op.etable_index = self.externs.index_of(op.external)

    def visit_warnop(self, op):
        op.string = self.strings.new(op.value)

    def visit_operation(self, op):
        pass

class NoOutputOpSkipper(object):
    def visit_nameop(self, op):
        pass

    def visit_stopop(self, op):
        pass

class Emitter(NoOutputOpSkipper):
    def __init__(self, write, commandline=None):
        self.__write = write
        self.wrap_asm = commandline is not None and commandline.wrap_asm

    def write(self, text):
        self.__write(text.encode("utf-8"))

    def write_asm(self, line, comment=None):
        if self.wrap_asm and line:
            line = r'  "%s\n"' % line.replace('"', r'\"')
        if comment is not None:
            line += "\t/* %s */" % comment
        line += "\n"
        self.write(line)

    def new_label(self):
        self.num_labels += 1
        return Label(str(self.num_labels))

    def emit(self, line, comment=None):
        if line.startswith("."):
            line = "\t" + line
        if not line.startswith("#") and self.__label is not None:
            line = "%s:%s" % (self.__label.name, line)
            self.__label = None
        self.write_asm(line, comment)

    def emit_newline(self):
        self.emit("")

    def emit_comment(self, comment):
        self.emit("", comment)

    def emit_label(self, label):
        if self.__label is not None:
            self.write_asm("%s:" % self.__label.name)
            self.__label = None
        self.__label = label
        label.emitted = True

    def __emit_constant(self, directive, value, comment):
        value = str(value)
        tmp = getattr(constants, value, None)
        if tmp is not None:
            if comment is None:
                comment = value
            else:
                comment = "%s (%s)" % (value, comment)
            if value.startswith("I8_OP_"):
                tmp -= 0x100
            value = tmp
        self.emit(".%s %s" % (directive, value), comment)

    def __emit_nbyte(self, n, value, comment):
        self.__emit_constant(("%sbyte" % n), value, comment)

    def emit_byte(self, value, comment=None):
        self.__emit_nbyte("", value, comment)

    def emit_2byte(self, value, comment=None):
        self.__emit_nbyte(2, value, comment)

    def emit_4byte(self, value, comment=None):
        self.__emit_nbyte(4, value, comment)

    def emit_8byte(self, value, comment=None):
        self.__emit_nbyte(8, value, comment)

    def emit_uleb128(self, value, comment=None):
        self.__emit_constant("uleb128", value, comment)

    def emit_sleb128(self, value, comment=None):
        self.__emit_constant("sleb128", value, comment)

    def emit_op(self, name, comment=None):
        widename = "I8_OP_" + name
        widecode = getattr(constants, widename, None)
        if widecode is not None:
            name = "GNU_wide_op"
        name = "DW_OP_" + name
        self.emit_byte(name, comment)
        if widecode is not None:
            self.emit_uleb128(widename)

    def visit_toplevel(self, toplevel):
        self.num_labels = 0
        self.__label = None
        self.wordsize = toplevel.wordsize
        bytes, check = divmod(self.wordsize, 8)
        assert check == 0
        self.emit_address = getattr(self, "emit_%dbyte" % bytes)
        if self.wrap_asm:
            self.write("__asm__ (\n")
        self.emit('.pushsection .note.infinity, "", "note"')
        self.emit(".balign 4")
        for node in toplevel.functions:
            node.accept(self)
        self.emit(".popsection")
        if self.wrap_asm:
            self.write("  );\n")

    def visit_function(self, function):
        debug_print("\n%s:\n%s\n" % (function.name.value, function.ops))
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
        # Build the strings and externals tables.
        function.accept(TableBuilder(self))

        # Emit the code chunks if required.
        if self.has_code(function):
            self.emit_chunk("codeinfo", 1, Emitter.emit_codeinfo, function)
            self.emit_chunk("bytecode", 3, Emitter.emit_bytecode, function)

        # Emit the remaining chunks.
        self.emit_chunk("signature", 2, Emitter.emit_signature)
        if self.externs.entries:
            self.emit_chunk("externals", 2, self.externs.emit)
        self.emit_chunk("strings", 1, self.strings.emit)

    def emit_chunk(self, name, version, emitfunc, *args):
        start = self.new_label()
        limit = self.new_label()
        self.emit_uleb128("I8_CHUNK_" + name.upper())
        self.emit_uleb128(version, "chunk version")
        self.emit_uleb128(limit - start, "chunk size")
        self.emit_label(start)
        emitfunc(self, *args)
        self.emit_label(limit)

    def emit_signature(self):
        self.emit_uleb128(self.provider.offset, "provider offset")
        self.emit_uleb128(self.name.offset, "name offset")
        self.emit_uleb128(self.paramtypes.offset, "param types offset")
        self.emit_uleb128(self.returntypes.offset, "return types offset")

    @staticmethod
    def has_code(function):
        skipper = NoOutputOpSkipper()
        try:
            for index, op in function.ops.stream:
                op.accept(skipper)
            return False
        except visitors.VisitError:
            return True

    def emit_codeinfo(self, function):
        self.emit_2byte(archspec.encode(self.wordsize), "archspec")
        self.emit_uleb128(function.max_stack, "max stack")

    def emit_bytecode(self, function):
        function.ops.accept(self)

    # Emit the bytecode

    def visit_operationstream(self, ops):
        self.jumps = ops.jumps
        self.labels = {}
        for op in ops.labels.keys():
            self.labels[op] = self.new_label()
        for index, op in ops.stream:
            label = self.labels.get(op, None)
            if label is not None:
                self.emit_label(label)
            op.accept(self)

    # Generic visitors that handle groups of operations.

    def visit_nooperandsop(self, op):
        self.emit_op(op.dwarfname, op.fileline)

    def visit_terminalop(self, op):
        assert op.is_branch or op.is_goto
        target = self.labels[self.jumps[op]]
        source = self.new_label()
        self.emit_op(op.dwarfname, op.fileline)
        self.emit_2byte(target - source)
        self.emit_label(source)

    # Visitors for operations that need specific handling.

    def visit_castop(self, op):
        self.emit_op("cast_%s2%s" % (op.old_type.basetype.name,
                                     op.new_type.basetype.name))
        self.emit_uleb128(op.slot)

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
        if op.type.basetype is types.PTRTYPE:
            self.emit_op("deref", op.fileline)
            return

        sizedtype = op.type.sizedtype
        operand = sizedtype.nbits
        if operand is None:
            operand = self.wordsize
        if sizedtype.is_signed:
            operand *= -1

        # "deref_int 0" used to mean a word-sized integer, but its
        # signedness was ambiguous so this use has been deprecated.
        assert operand != 0

        self.emit_op("deref_int", op.fileline)
        self.emit_sleb128(operand)

    def visit_loadop(self, op):
        self.emit_op(op.dwarfname, op.fileline)
        if op.is_pick:
            if op.pickslot > 1:
                self.emit_byte(op.pickslot)
        else:
            assert op.is_loadext
            if op.external.basetype is PTRTYPE:
                self.emit_address(op.external.name)
            else:
                assert op.external.type.is_function
                self.emit_uleb128(op.etable_index)

    def visit_plusuconst(self, op):
        self.emit_op("plus_uconst", op.fileline)
        self.emit_uleb128(op.value)

    def visit_warnop(self, op):
        self.emit_op("warn", op.fileline)
        self.emit_uleb128(op.string.offset, op.string.quoted)

# -*- coding: utf-8 -*-
# Copyright (C) 2015 Red Hat, Inc.
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

from .. import constants
from ..compat import fwrite, str
from . import logger
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
    def __init__(self, strings, default_provider):
        self.strings = strings
        self.default_provider = default_provider
        self.entries = []

    def visit_external(self, external):
        basetype = external.typename.type.basetype
        fullname = external.name.value
        if basetype is PTRTYPE:
            self.entries.append(RelAddr(fullname))
        else:
            assert basetype.is_function
            provider = fullname.provider or self.default_provider
            self.entries.append(FuncRef(*map(self.strings.new, (
                provider,
                fullname.name,
                "".join((t.encoding for t in basetype.paramtypes)),
                "".join((t.encoding for t in basetype.returntypes))))))

    def emit(self, emitter):
        for entry, index in zip(self.entries, range(len(self.entries))):
            entry.emit(emitter, "extern %d " % index)

class RelAddr(object):
    def __init__(self, name):
        self.name = str(name)

    def emit(self, emitter, prefix):
        emitter.emit_byte("I8_TYPE_RELADDR", prefix + "type")
        emitter.emit_uleb128(self.name, prefix + "relative address")

class FuncRef(object):
    def __init__(self, provider, name, params, returns):
        self.provider = provider
        self.name = name
        self.params = params
        self.returns = returns

    def emit(self, emitter, prefix):
        emitter.emit_byte("I8_TYPE_RAWFUNC", prefix + "type")
        emitter.emit_uleb128(self.provider.offset, prefix + "provider offset")
        emitter.emit_uleb128(self.name.offset, prefix + "name offset")
        emitter.emit_uleb128(self.params.offset, prefix + "ptypes offset")
        emitter.emit_uleb128(self.returns.offset, prefix + "rtypes offset")

class NoOutputOpSkipper(object):
    def visit_castop(self, op):
        pass

    def visit_nameop(self, op):
        pass

    def visit_stopop(self, op):
        pass

class Emitter(NoOutputOpSkipper):
    def __init__(self, write):
        self.__write = write

    def write(self, text):
        self.__write(text.encode("utf-8"))

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

    def maybe_define_constant(self, name):
        if name in self.__constants:
            return
        value = getattr(constants, name, None)
        if value is None:
            return
        if isinstance(value, str):
            format = "'%s'"
        else:
            format = "0x%02x"
        value = format % value
        self.emit("#define %s %s" % (name, value))
        self.__constants[name] = True

    def to_string(self, value):
        value = str(value)
        if not (value[0].isdigit() or value[0] == "-"):
            self.maybe_define_constant(value)
            if value.startswith("I8_OP_"):
                value += " - 0x100"
        return value

    def __emit_nbyte(self, n, value, comment):
        self.emit((".%sbyte " % n) + self.to_string(value), comment)

    def emit_byte(self, value, comment=None):
        self.__emit_nbyte("", value, comment)

    def emit_2byte(self, value, comment=None):
        self.__emit_nbyte(2, value, comment)

    def emit_4byte(self, value, comment=None):
        self.__emit_nbyte(4, value, comment)

    def emit_8byte(self, value, comment=None):
        self.__emit_nbyte(8, value, comment)

    def emit_uleb128(self, value, comment=None):
        self.emit(".uleb128 " + self.to_string(value), comment)

    def emit_sleb128(self, value, comment=None):
        self.emit(".sleb128 " + self.to_string(value), comment)

    def emit_op(self, name, comment=None):
        if not self.__BOM_emitted:
            self.emit_2byte("I8_BYTE_ORDER_MARK")
            self.__BOM_emitted = True
        widename = "I8_OP_" + name
        widecode = getattr(constants, widename, None)
        if widecode is not None:
            name = "GNU_wide_op"
        assert name != "addr" # See XXX UNWRITTEN DOCS.
        name = "DW_OP_" + name
        self.emit_byte(name, comment)
        if widecode is not None:
            self.emit_uleb128(widename)

    def visit_toplevel(self, toplevel):
        self.num_labels = 0
        self.__label = None
        self.__constants = {}
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
        strings = StringTable()
        self.externs = ExternTable(strings, function.name.provider)

        # Populate the string and extern tables
        self.provider = strings.new(function.name.provider)
        self.name = strings.new(function.name.shortname)
        self.paramtypes = strings.new()
        self.returntypes = strings.new()
        for node in function.entry_stack:
            node.accept(self)
        function.returntypes.accept(self)
        strings.layout_table(self.new_label)

        # Emit the chunks
        self.emit_chunk("info", 1, Emitter.emit_info, function)
        if self.has_code(function):
            self.emit_chunk("code", 1, Emitter.emit_code, function)
        if self.externs.entries:
            self.emit_chunk("etab", 1, self.externs.emit)
        self.emit_chunk("stab", 1, strings.emit)

    def emit_chunk(self, name, version, emitfunc, *args):
        start = self.new_label()
        limit = self.new_label()
        self.emit_uleb128("I8_CHUNK_" + name.upper())
        self.emit_uleb128(version, "chunk version")
        self.emit_uleb128(limit - start, "chunk size")
        self.emit_label(start)
        emitfunc(self, *args)
        self.emit_label(limit)

    def emit_info(self, function):
        self.emit_uleb128(self.provider.offset, "provider offset")
        self.emit_uleb128(self.name.offset, "name offset")
        self.emit_uleb128(self.paramtypes.offset, "param types offset")
        self.emit_uleb128(self.returntypes.offset, "return types offset")
        self.emit_uleb128(function.max_stack, "max stack")

    @staticmethod
    def has_code(function):
        ops = sorted(function.ops.ops.items())
        skipper = NoOutputOpSkipper()
        try:
            for index, op in ops:
                op.accept(skipper)
            return False
        except AttributeError:
            return True

    def emit_code(self, function):
        self.__BOM_emitted = False
        function.ops.accept(self)

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

    def visit_external(self, external):
        external.accept(self.externs)

    # Emit the bytecode

    def visit_operationstream(self, stream):
        debug_print("%s\n" % stream)
        self.jumps = stream.jumps
        self.labels = {}
        for op in stream.labels.keys():
            self.labels[op] = self.new_label()
        ops = sorted(stream.ops.items())
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
    visit_overop = emit_simple_op

    def visit_pickop(self, op):
        if op.slot == 0:
            self.emit_op("dup", op.fileline)
        elif op.slot == 1:
            self.emit_op("over", op.fileline)
        else:
            self.emit_op("pick", op.fileline)
            self.emit_byte(op.slot)

    def visit_plusuconst(self, op):
        self.emit_op("plus_uconst", op.fileline)
        self.emit_uleb128(op.value)

    visit_rotop = emit_simple_op
    visit_subop = emit_simple_op
    visit_swapop = emit_simple_op
    visit_unaryop = emit_simple_op

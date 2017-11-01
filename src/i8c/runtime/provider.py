# -*- coding: utf-8 -*-
# Copyright (C) 2015-17 Red Hat, Inc.
# This file is part of the Infinity Note Execution Environment.
#
# The Infinity Note Execution Environment is free software; you can
# redistribute it and/or modify it under the terms of the GNU Lesser
# General Public License as published by the Free Software Foundation;
# either version 2.1 of the License, or (at your option) any later
# version.
#
# The Infinity Note Execution Environment is distributed in the hope
# that it will be useful, but WITHOUT ANY WARRANTY; without even the
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with the Infinity Note Execution Environment; if not,
# see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from ..compat import integer
from .. import constants
from . import ProviderError, SymbolError
import arpy
from elftools.elf import elffile
from elftools.elf import relocation
from elftools.elf import sections
import struct
import sys
import weakref
try:
    import builtins
except ImportError: # pragma: no cover
    import __builtin__ as builtins

class Provider(object):
    @classmethod
    def open(cls, filename_or_fileobj, filename=None):
        if hasattr(filename_or_fileobj, "read"):
            fp = filename_or_fileobj
            if filename is None:
                filename = getattr(fp, "name", None)
            needs_close = False
        else:
            assert filename is None
            filename = filename_or_fileobj
            fp = builtins.open(filename_or_fileobj, "rb")
            needs_close = True
        offset = fp.tell()
        header = fp.read(max((len(c.MAGIC) for c in cls.CLASSES)))
        for c in cls.CLASSES:
            if header.startswith(c.MAGIC):
                fp.seek(offset)
                return c(filename, fp, needs_close)
        raise ProviderError(filename, "unhandled file")

    def __init__(self, filename, fp, needs_close):
        self.filename = filename
        self.fp = fp
        self.needs_close = needs_close

    def __exit__(self, type, value, tb):
        if self.needs_close:
            self.fp.close()

class Archive(Provider):
    MAGIC = b"!<arch>\n"

    def __enter__(self):
        self.__ar = arpy.Archive(self.filename, self.fp)
        self.__ar.read_all_headers()
        return self

    def __exit__(self, type, value, tb):
        super(Archive, self).__exit__(type, value, tb)
        del self.__ar

    @property
    def infinity_notes(self):
        for fp in self.__ar.archived_files.values():
            fn = "%s[%s]" % (self.filename, fp.header.name.decode("utf-8"))
            with Provider.open(fp, fn) as fp:
                for note in fp.infinity_notes:
                    yield note

class ELF(Provider):
    MAGIC = constants.ELFMAG

    def __enter__(self):
        self.__elf = elffile.ELFFile(self.fp)
        self.wordsize = self.__elf.elfclass
        self.byteorder = self.__elf.little_endian and b"<" or b">"
        self.__symbols = None
        return self

    def __exit__(self, type, value, tb):
        super(ELF, self).__exit__(type, value, tb)
        del self.__elf

    @property
    def note_sections(self):
        for sect in self.__elf.iter_sections():
            if isinstance(sect, sections.NoteSection):
                yield NoteSection(self, sect)

    @property
    def infinity_notes(self):
        for sect in self.note_sections:
            for note in sect.infinity_notes:
                yield note

    @property
    def symbols(self):
        if self.__symbols is None:
            self.__symbols = {}
            for sect in self.__elf.iter_sections():
                if not isinstance(sect, sections.SymbolTableSection):
                    continue
                for sym in sect.iter_symbols():
                    name = sym.name
                    if not name:
                        continue
                    # Skip aarch64 mapping symbols.
                    if (name[0] == "$"
                          and sym.entry.st_info.type == "STT_NOTYPE"
                          and sym.entry.st_info.bind == "STB_LOCAL"
                          and sym.entry.st_size == 0):
                        continue
                    addr = sym.entry.st_value
                    if addr == 0 and sym.entry.st_info.bind != "STB_GLOBAL":
                        continue
                    orig = self.__symbols.get(addr, [])
                    if name not in (sym2.name for sym2 in orig):
                        if not addr in self.__symbols:
                            self.__symbols[addr] = orig
                        orig.append(sym)
        return self.__symbols

    def __get_named_symbol(self, symtab, reloc):
        symbol = symtab.get_symbol(reloc["r_info_sym"])
        if symbol.name:
            return symbol
        # Handle cases where the target of a relocation is an
        # offset into a section.
        if symbol.entry.st_info.type == "STT_SECTION":
            assert symbol.entry.st_value == 0
            st_shndx = symbol.entry.st_shndx
            r_addend = getattr(reloc.entry, "r_addend", 0)
            for symbol in symtab.iter_symbols():
                if (symbol.entry.st_shndx == st_shndx
                        and symbol.entry.st_value == r_addend
                        and symbol.name):
                    return symbol
        raise ProviderError(self.filename, "unhandled relocation")

    def relocations_for(self, sect):
        result = {}
        reloc_handler = relocation.RelocationHandler(self.__elf)
        reloc_sect = reloc_handler.find_relocations_for_section(sect)
        if reloc_sect is None:
            return result
        symtab = self.__elf.get_section(reloc_sect["sh_link"])
        for reloc in reloc_sect.iter_relocations():
            symbol = self.__get_named_symbol(symtab, reloc)
            offset = reloc["r_offset"]
            if offset not in result:
                result[offset] = []
            result[offset].append(symbol)
        return result

    def symbols_matching(self, addr):
        return self.symbols.get(addr, [])

Provider.CLASSES = [Archive, ELF]
open = Provider.open

class NoteSection(object):
    def __init__(self, elf, section):
        self.__elf = elf
        self.__sect = weakref.ref(section)
        self.offset = section["sh_offset"]
        self.data = section.data()
        self.__relocs = None

    @property
    def filename(self):
        return self.__elf.filename

    @property
    def wordsize(self):
        return self.__elf.wordsize

    @property
    def byteorder(self):
        return self.__elf.byteorder

    @property
    def infinity_notes(self):
        for note in self.__sect().iter_notes():
            if (note.n_name in ("GNU", "GNU\0")
                and note.n_type in (constants.NT_GNU_INFINITY,
                                    "NT_GNU_INFINITY")):
                yield Note(self, note)

    @property
    def relocations(self):
        if self.__relocs is None:
            self.__relocs = self.__elf.relocations_for(self.__sect())
        return self.__relocs

    def relocs_at(self, offset):
        return self.relocations.get(offset, [])

    def symbols_at(self, offset):
        fmt = self.byteorder + {32: b"I", 64: b"Q"}[self.wordsize]
        size = struct.calcsize(fmt)
        addr = struct.unpack(fmt, self.data[offset:offset + size])[0]

        # First try relocations.  This branch handles ET_REL
        # (object files, including those in static libraries).
        result = self.relocs_at(offset)
        if result:
            return result

        # Fall back to symbol table lookup.  This branch does
        # ET_DYN (shared libraries) and ET_EXEC (executables).
        return self.__elf.symbols_matching(addr)

class NoteSlice(object):
    def __init__(self, section, key):
        assert isinstance(key, slice)
        assert key.step in (None, 1)
        self.__sect = section

        assert key.start >= 0
        self.start = key.start
        assert key.stop <= len(section.data)
        self.limit = key.stop

    def __len__(self):
        return self.limit - self.start

    def __getitem__(self, key):
        if isinstance(key, integer):
            result = self.data[key]
            if isinstance(result, int):
                result = chr(result)
            return result

        assert isinstance(key, slice)
        assert key.step in (None, 1)

        start = self.start
        if key.start is not None:
            start += key.start
            assert start <= self.limit
        if key.stop is not None:
            limit = self.start + key.stop
            assert limit <= self.limit
        else:
            limit = self.limit
        return NoteSlice(self.__sect, slice(start, limit))

    def __add__(self, offset):
        start = self.start + offset
        assert start <= self.limit
        return NoteSlice(self.__sect, slice(start, self.limit))

    @property
    def srcname(self):
        return self.__sect.filename

    @property
    def srcoffset(self):
        return self.__sect.offset + self.start

    @property
    def wordsize(self):
        return self.__sect.wordsize

    @property
    def byteorder(self):
        return self.__sect.byteorder

    @property
    def data(self):
        return self.__sect.data[self.start:self.limit]

    @property
    def text(self):
        text = self.data
        if sys.version_info >= (3,):
            text = "".join(map(chr, text))
        assert isinstance(text, str)
        return text

    @property
    def symbol_names(self):
        symbols = self.__sect.symbols_at(self.start)
        if not symbols:
            raise SymbolError(self)
        return [symbol.name for symbol in symbols]

class Note(NoteSlice):
    def __init__(self, section, note):
        start = (note.n_offset
                 - section.offset  # Convert to section offset.
                 + 12              # n_namesz, n_descsz, n_type.
                 + (((note.n_namesz - 1) | 3) + 1))  # n_name + padding.
        limit = start + note.n_descsz
        super(Note, self).__init__(section, slice(start, limit))

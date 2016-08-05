# -*- coding: utf-8 -*-
# Copyright (C) 2015-16 Red Hat, Inc.
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
from . import ProviderError
import arpy
from elftools.elf import elffile
from elftools.elf import relocation
from elftools.elf import sections
import struct
import sys
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
        self.ar = arpy.Archive(self.filename, self.fp)
        self.ar.read_all_headers()
        return self

    def __exit__(self, type, value, tb):
        super(Archive, self).__exit__(type, value, tb)
        del self.ar

    @property
    def infinity_notes(self):
        for fp in self.ar.archived_files.values():
            fn = "%s[%s]" % (self.filename, fp.header.name.decode("utf-8"))
            with Provider.open(fp, fn) as fp:
                for note in fp.infinity_notes:
                    yield note

class ELF(Provider):
    MAGIC = b"\x7fELF"

    def __enter__(self):
        self.elf = elffile.ELFFile(self.fp)
        self.wordsize = self.elf.elfclass
        self.byteorder = self.elf.little_endian and b"<" or b">"
        self.__symbols = None
        self.__relocs = {}
        return self

    def __exit__(self, type, value, tb):
        super(ELF, self).__exit__(type, value, tb)
        del self.__relocs, self.__symbols, self.elf

    @property
    def infinity_notes(self):
        for sect in self.elf.iter_sections():
            if not isinstance(sect, sections.NoteSection):
                continue
            for note in sect.iter_notes():
                # pyelftools thinks n_name is "GNU", but I think
                # it should really be "GNU\0".  We'll allow both.
                if note["n_name"] not in ("GNU", "GNU\0"):
                    continue
                # Currently pyelftools returns the numeric value,
                # but at some point the constant will be added in
                # which case it's going to return a string.
                if note["n_type"] not in (constants.NT_GNU_INFINITY,
                                          "NT_GNU_INFINITY"):
                    continue
                # The inner-format part (the actual Infinity note)
                # is in the desc field.  Work out where that is in
                # relation to the containing ELF.
                elf_note_hdr_size = 12 # n_namesz, n_descsz, n_type
                elf_note_namesz_pad = ((note["n_namesz"] - 1) | 3) + 1
                i8_note_offset = (note["n_offset"]
                                  + elf_note_hdr_size
                                  + elf_note_namesz_pad)
                i8_note_bytes = note["n_desc"]
                if sys.version_info >= (3,):
                    # pyelftools converts to string, but we want bytes
                    i8_note_bytes = i8_note_bytes.encode("latin-1")
                assert len(i8_note_bytes) == note["n_descsz"]
                yield NoteSlice(Note(self, sect, i8_note_offset,
                                     i8_note_bytes),
                                slice(0, note["n_descsz"]))

    @property
    def symbols(self):
        if self.__symbols is None:
            self.__symbols = {}
            for sect in self.elf.iter_sections():
                if not isinstance(sect, sections.SymbolTableSection):
                    continue
                for sym in sect.iter_symbols():
                    addr = sym["st_value"]
                    if addr not in self.__symbols:
                        self.__symbols[addr] = [sym.name]
                    else:
                        self.__symbols[addr].append(sym.name)
        return self.__symbols

    def __get_named_symbol(self, symtab, index):
        symbol = symtab.get_symbol(index)
        if symbol.name:
            return symbol
        # XXX this symbol is the start of a section?
        assert symbol.entry["st_info"]["type"] == "STT_SECTION"
        assert symbol.entry["st_value"] == 0
        st_shndx = symbol.entry["st_shndx"]
        for symbol in symtab.iter_symbols():
            if (symbol.entry["st_shndx"] == st_shndx
                    and symbol.entry["st_value"] == 0
                    and symbol.name):
                return symbol
        raise ProviderError(self.filename, "unhandled relocation")

    def relocations_for(self, sect):
        relocs = self.__relocs.get(sect.name, None)
        if relocs is None:
            relocs = self.__relocs[sect.name] = {}
            reloc_handler = relocation.RelocationHandler(self.elf)
            reloc_sect = reloc_handler.find_relocations_for_section(sect)
            symtab = self.elf.get_section(reloc_sect["sh_link"])
            for reloc in reloc_sect.iter_relocations():
                symbol = self.__get_named_symbol(symtab, reloc["r_info_sym"])
                relocs[reloc["r_offset"]] = symbol.name
        return relocs

    def symbol_names_at(self, section, offset, addr):
        if addr == 0:
            return [self.relocations_for(section)[offset]]
        else:
            return self.symbols[addr]

Provider.CLASSES = [Archive, ELF]
open = Provider.open

class Note(object):
    def __init__(self, elf, section, offset, bytes):
        self.elf = elf
        self.section = section
        self.offset = offset # of first byte of n_desc in ELF
        self.bytes = bytes

    @property
    def filename(self):
        return self.elf.filename

    @property
    def wordsize(self):
        return self.elf.wordsize

    @property
    def byteorder(self):
        return self.elf.byteorder

    def symbol_names_at(self, offset):
        fmt = self.byteorder + {32: b"I", 64: b"Q"}[self.wordsize]
        size = struct.calcsize(fmt)
        addr = struct.unpack(fmt, self.bytes[offset:offset + size])[0]
        offset = self.offset + offset - self.section["sh_offset"]
        return self.elf.symbol_names_at(self.section, offset, addr)

class NoteSlice(object):
    def __init__(self, note, key):
        assert isinstance(key, slice)
        assert key.step in (None, 1)
        self.note = note

        assert key.start >= 0
        self.start = key.start
        assert key.stop <= len(note.bytes)
        self.limit = key.stop

    def __len__(self):
        return self.limit - self.start

    def __getitem__(self, key):
        if isinstance(key, integer):
            result = self.bytes[key]
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
        return NoteSlice(self.note, slice(start, limit))

    def __add__(self, offset):
        start = self.start + offset
        assert start <= self.limit
        return NoteSlice(self.note, slice(start, self.limit))

    @property
    def filename(self):
        return self.note.filename

    @property
    def wordsize(self):
        return self.note.wordsize

    @property
    def byteorder(self):
        return self.note.byteorder

    @property
    def bytes(self):
        return self.note.bytes[self.start:self.limit]

    @property
    def text(self):
        text = self.bytes
        if sys.version_info >= (3,):
            text = "".join(map(chr, text))
        assert isinstance(text, str)
        return text

    @property
    def symbol_names(self):
        return self.note.symbol_names_at(self.start)

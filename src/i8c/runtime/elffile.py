# -*- coding: utf-8 -*-
# Copyright (C) 2015 Red Hat, Inc.
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
from . import ELFFileError
import struct
import sys
import weakref

class ELFFile(object):
    ELFCLASS32 = 1
    ELFCLASS64 = 2
    WORDSIZES = {ELFCLASS32: 32, ELFCLASS64: 64}

    ELFDATA2LSB = 1
    ELFDATA2MSB = 2
    BYTEORDERS = {ELFDATA2LSB: b"<", ELFDATA2MSB: b">"}

    __open = open

    def __init__(self, filename):
        self.filename = filename
        with self.__open(self.filename, "rb") as fp:
            self.bytes = fp.read()
        self.start, self.limit = 0, len(self.bytes)
        hdrfmt = b"4sBB"
        hdrlen = struct.calcsize(hdrfmt)
        magic, ei_class, ei_data = struct.unpack(hdrfmt, self.bytes[:hdrlen])
        if magic != b"\x7fELF":
            raise ELFFileError(filename, "not an ELF file")
        try:
            self.wordsize = self.WORDSIZES[ei_class]
            self.byteorder = self.BYTEORDERS[ei_data]
        except KeyError:
            raise ELFFileError(filename, "unhandled ELF file")

    @property
    def infinity_notes(self):
        # XXX this is not a real ELF parser!
        notename = b"GNU\0"
        markerfmt = self.byteorder + ("I%ds" % len(notename)).encode("utf-8")
        marker = struct.pack(markerfmt, constants.NT_GNU_INFINITY, notename)
        hdrfmt = self.byteorder + b"2I"
        start = hdrsz = struct.calcsize(hdrfmt)
        while True:
            start = self.bytes.find(marker, start)
            if start < 0:
                break
            start -= hdrsz
            namesz, descsz = struct.unpack(
                hdrfmt, self.bytes[start:start + hdrsz])
            assert namesz == len(notename)
            descstart = start + hdrsz + struct.calcsize("I") + len(notename)
            desclimit = descstart + descsz
            yield self[descstart:desclimit]
            start = desclimit

    def __getitem__(self, key):
        return ELFSlice(weakref.ref(self), key)

class ELFSlice(object):
    def __init__(self, elffile, ourslice):
        assert isinstance(ourslice, slice)
        assert ourslice.step in (None, 1)
        self.elffile = elffile

        elffile = elffile()
        self.filename = elffile.filename
        self.wordsize = elffile.wordsize
        self.byteorder = elffile.byteorder

        assert ourslice.start >= 0
        self.start = elffile.start + ourslice.start
        assert self.start <= elffile.limit
        assert ourslice.stop >= 0
        self.limit = elffile.start + ourslice.stop
        assert self.limit <= elffile.limit

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
        return self.elffile()[start:limit]

    def __len__(self):
        return self.limit - self.start

    def __add__(self, offset):
        start = self.start + offset
        assert start <= self.limit
        return self.elffile()[start:self.limit]

    @property
    def bytes(self):
        return self.elffile().bytes[self.start:self.limit]

    @property
    def text(self):
        text = self.bytes
        if sys.version_info >= (3,):
            text = "".join(map(chr, text))
        assert isinstance(text, str)
        return text

open = ELFFile

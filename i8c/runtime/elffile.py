# -*- coding: utf-8 -*-
from .. import constants
from . import ELFFileError
import struct
import weakref

class ELFFile(object):
    ELFCLASS32 = 1
    ELFCLASS64 = 2
    WORDSIZES = {ELFCLASS32: 32, ELFCLASS64: 64}

    ELFDATA2LSB = 1
    ELFDATA2MSB = 2
    BYTEORDERS = {ELFDATA2LSB: "<", ELFDATA2MSB: ">"}

    __open = open

    def __init__(self, filename):
        self.filename = filename
        self.bytes = self.__open(self.filename).read()
        self.start, self.limit = 0, len(self.bytes)
        hdrfmt = "4sBB"
        hdrlen = struct.calcsize(hdrfmt)
        magic, ei_class, ei_data = struct.unpack(hdrfmt, self.bytes[:hdrlen])
        if magic != "\x7fELF":
            raise ELFFileError(filename, "not an ELF file")
        try:
            self.wordsize = self.WORDSIZES[ei_class]
            self.byteorder = self.BYTEORDERS[ei_data]
        except KeyError:
            raise ELFFileError(filename, "unhandled ELF file")

    @property
    def infinity_notes(self):
        notename = "GNU\0"
        markerfmt = "%sI%dsH" % (self.byteorder, len(notename))
        marker = struct.pack(markerfmt, constants.NT_GNU_INFINITY,
                             notename, constants.I8_FUNCTION_MAGIC)
        hdrfmt = self.byteorder + "2I"
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
        if isinstance(key, (int, long)):
            return self.bytes[key]

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

open = ELFFile

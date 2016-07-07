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

from ..compat import join_bytes
import struct

class Builder(object):
    def __init__(self, mem):
        self.mem = mem

    @property
    def env(self):
        return self.mem.env

    def __enter__(self):
        self.blocks = []
        self.symbols = {}
        return self

    def alloc(self, name=None):
        result = AllocatedBlock(self.env.wordsize)
        self.blocks.append(result)
        if name is not None:
            assert not name in self.symbols
            self.symbols[name] = result
        return result

    def __exit__(self, type, value, traceback):
        if type is None:
            # Allocate block addresses.
            addr = 0x10000000
            for block in self.blocks:
                block.location = addr
                addr += block.length
                addr += 1 # empty space to catch overflows
                addr += (16 - addr % 16) # align for printing
            # Store the data.
            for block in self.blocks:
                block.write_into(self.mem)
            # Install the symbols.
            for name, block in self.symbols.items():
                self.env.register_symbol(name, block.location)
        # Avoid circular references.
        for block in self.blocks:
            del block.fields

class Block(object):
    def __init__(self, offset, fields):
        self.offset = offset
        self.fields = fields

    def __add__(self, offset):
        return OffsetBlock(self, offset)

    def store_i8(self, offset, value):
        self.__store(offset, value, 8, True)

    def store_u8(self, offset, value):
        self.__store(offset, value, 8, False)

    def store_i16(self, offset, value):
        self.__store(offset, value, 16, True)

    def store_u16(self, offset, value):
        self.__store(offset, value, 16, False)

    def store_i32(self, offset, value):
        self.__store(offset, value, 32, True)

    def store_u32(self, offset, value):
        self.__store(offset, value, 32, False)

    def store_i64(self, offset, value):
        self.__store(offset, value, 64, True)

    def store_u64(self, offset, value):
        self.__store(offset, value, 64, False)

    def store_ixx(self, offset, value):
        self.__store(offset, value, self.wordsize, True)

    def store_uxx(self, offset, value):
        self.__store(offset, value, self.wordsize, False)

    def store_ptr(self, offset, value):
        if value in (0, None): # 0 == NULL
            value = 0
        else:
            assert isinstance(value, Block)
        self.store_uxx(offset, value)

    def __store(self, offset, value, nbits, is_signed):
        offset += self.offset
        value = Value(value, nbits, is_signed)
        self.fields[offset] = value
        for i in range(1, value.length):
            self.fields[offset + i] = None

    @property
    def length(self):
        if not self.fields:
            # Really 0, but returning 1 leaves an empty sentinel
            # cell to cause an error in the event this pointer to
            # uninitialized memory is dereferenced.
            return 1
        return max(self.fields.keys()) + 1

    def write_into(self, mem):
        for offset, value in sorted(self.fields.items()):
            if value is not None:
                value.write_into(mem, self.location + offset)

class AllocatedBlock(Block):
    def __init__(self, wordsize):
        Block.__init__(self, 0, {})
        self.wordsize = wordsize
        self.offset = 0

class OffsetBlock(Block):
    def __init__(self, parent, offset):
        Block.__init__(self, parent.offset + offset, parent.fields)
        self.parent = parent

    @property
    def wordsize(self):
        return self.parent.wordsize

    @property
    def location(self):
        root = self
        while isinstance(root, OffsetBlock):
            root = root.parent
        return root.location + self.offset

class Value(object):
    FORMATS = {8: b"b", 16: b"h", 32: b"i", 64: b"q"}

    def __init__(self, value, nbits, is_signed):
        self.value = value
        self.format = self.FORMATS[nbits]
        if not is_signed:
            self.format = self.format.upper()
        self.length = struct.calcsize(self.format)
        assert self.length * 8 == nbits

    def write_into(self, mem, location):
        value = self.value
        if isinstance(value, Block):
            value = value.location
        bytes = struct.pack(mem.env.byteorder + self.format, value)
        mem.write(location, bytes)

class Memory(object):
    def __init__(self, env):
        self.env = env
        self.cells = {}

    def builder(self):
        return Builder(self)

    def getbyte(self, location):
        try:
            return self.cells[location]
        except KeyError:
            # XXX this should be an exception
            print("getbyte(%x):\n%s" % (location, self))
            raise

    def putbyte(self, location, value):
        assert not location in self.cells
        self.cells[location] = value

    def read(self, location, size):
        return join_bytes(self.getbyte(location + offset)
                          for offset in range(size))

    def write(self, location, bytes):
        for byte, offset in zip(bytes, range(len(bytes))):
            self.putbyte(location + offset, byte)

    def __str__(self):
        tmp = {}
        for location, content in sorted(self.cells.items()):
            col = location % 16
            row = location - col
            if not row in tmp:
                tmp[row] = [None] * 16
            tmp[row][col] = content
        lines = []
        locfmt = "  %%0%dx: " % (self.env.wordsize // 4)
        lastloc = None
        for location, cells in sorted(tmp.items()):
            if lastloc not in (None, location - 16):
                lines.append("   ...")
            line = [locfmt % location]
            for cell in cells:
                if cell is None:
                    cell = "--"
                else:
                    cell = "%02x" % cell
                line.append(cell)
            line.insert(9, "")
            lines.append(" ".join(line))
            lastloc = location
        return "\n".join(lines)

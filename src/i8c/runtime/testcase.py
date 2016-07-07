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

from ..compat import strtoint_c
from . import I8XError, HeaderFileError, TestFileError
from . import memory
import copy
import inspect
import os
import platform
import struct
import weakref
try:
    import unittest2 as unittest
except ImportError: # pragma: no cover
    import unittest

class BaseTestCase(unittest.TestCase):
    def run(self, *args, **kwargs):
        self.memory = memory.Memory(self)
        self.addCleanup(delattr, self, "memory")
        self.__symbols = {}
        return unittest.TestCase.run(self, *args, **kwargs)

    def register_symbol(self, name, value):
        """Hook method for registering a symbol."""
        assert not name in self.__symbols
        self.__symbols[name] = value

    def lookup_symbol(self, name):
        """Hook method for resolving a symbol name to an address."""
        return self.__symbols[name]

    def read_memory(self, fmt, addr):
        """Hook method for reading bytes from memory."""
        return self.memory.read(addr, struct.calcsize(fmt))

    def warn_caller(self, msg):
        """Hook method for warning the caller about something."""
        self.fail("unexpected warning: " + msg)

class TestCase(BaseTestCase):
    include_path = []

    @staticmethod
    def __testcase_frame():
        frame = inspect.currentframe()
        if frame is None:
            raise I8XError("not available on "
                           + platform.python_implementation())
        return frame.f_back.f_back

    @classmethod
    def import_builtin_constants(cls):
        frame = cls.__testcase_frame()
        frame.f_globals.update({"NULL": 0, "FALSE": 0, "TRUE": 1})

    @classmethod
    def import_constants_from(cls, filename):
        frame = cls.__testcase_frame()
        path = copy.copy(cls.include_path)
        path.insert(0, os.path.dirname(frame.f_code.co_filename))
        for try_dir in path:
            try_filename = os.path.join(try_dir, filename)
            if os.path.exists(try_filename):
                filename = try_filename
                break
        else:
            raise TestFileError(filename, "not found in: " + repr(path))
        lines = open(filename).readlines()
        for line, linenumber in zip(lines, range(1, len(lines) + 1)):
            bits = line.strip().split()
            try:
                assert len(bits) == 3 and bits[0] == "#define"
                name, value = bits[1:]
                value = strtoint_c(value, I8XError)
                frame.f_globals[name] = value
            except:
                raise HeaderFileError(filename, linenumber)

    def run(self, *args, **kwargs):
        self.addCleanup(self.__restore_env, self.i8ctx.env)
        self.i8ctx.env = self
        return BaseTestCase.run(self, *args, **kwargs)

    def __restore_env(self, saved_env):
        self.i8ctx.env = saved_env

    @property
    def wordsize(self):
        return self.i8ctx.wordsize

    @property
    def byteorder(self):
        return self.i8ctx.byteorder

    def implement(self, func, args, rets):
        provider, name = func.split("::")
        setattr(self, "%s_%s_impl" % (provider, name),
                StubImpl(weakref.ref(self), args, rets))

class StubImpl(object):
    def __init__(self, tref, args, rets):
        self.tref = tref
        self.args = args
        self.rets = rets

    def __call__(self, *args):
        self.tref().assertEqual(args, self.args)
        if len(self.rets) == 1:
            return self.rets[0]
        else:
            return self.rets

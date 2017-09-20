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

from ..compat import strtoint_c
from .core import unittest, TestObject, TempSetAttr
from . import *
from . import memory
import copy
import inspect
import os
import platform
import struct

class BaseTestCase(unittest.TestCase):
    def run(self, *args, **kwargs):
        return unittest.TestCase.run(self, *args, **kwargs)

    def read_memory(self, fmt, addr):
        """Hook method for reading bytes from memory."""
        return self.memory.read(addr, struct.calcsize(fmt))

    def warn_caller(self, signature, msg):
        """Hook method for warning the caller about something."""
        self.fail("%s: unexpected warning: %s" % (signature,
                                                  repr(msg).lstrip("u")))

    class provide(object):
        """Decorator for Infinity functions provided by the test."""
        def __init__(self, signature):
            self.signature = signature

        def __call__(self, impl):
            return UserFunction(self.signature, impl)

    def _install_user_functions(self, ctx):
        for attr in dir(self):
            try:
                func = getattr(self, attr)
            except AttributeError:
                continue
            if isinstance(func, UserFunction):
                ctx.override(func.bind_to(self))

    def _install_context(self, ctx):
        """Temporarily install the specified context."""
        return TempSetAttr(self, "_ctx", ctx)

    @property
    def wordsize(self):
        return self._ctx.wordsize

    @property
    def byteorder(self):
        return self._ctx.byteorder

    @property
    def register_symbol(self):
        return self._ctx.register_symbol

    @property
    def to_signed(self):
        return self._ctx.to_signed

    @property
    def to_unsigned(self):
        return self._ctx.to_unsigned

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
        with Context(self) as ctx:
            self.__ctxp.populate(ctx)
            self._install_user_functions(ctx)
            with self._install_context(ctx):
                self.memory = memory.Memory(self)
                return BaseTestCase.run(self, *args, **kwargs)

    @property
    def call(self):
        return self._ctx.call

class UserFunction(object):
    def __init__(self, signature, impl):
        self.signature = signature
        self.impl = impl

    def __call__(self, *args):
        raise RuntimeError(self.signature)

    def bind_to(self, env):
        return BoundUserFunction(env, self)

class BoundUserFunction(TestObject):
    def __init__(self, env, unbound):
        super(BoundUserFunction, self).__init__(env)
        self.unbound = unbound

    @property
    def signature(self):
        return self.unbound.signature

    @property
    def impl(self, *args):
        return self.unbound.impl.__get__(self.env, self.unbound.impl)

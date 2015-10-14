# -*- coding: utf-8 -*-
from . import I8XError, HeaderFileError, TestFileError
import copy
import inspect
import os
import platform
try:
    import unittest2 as unittest
except ImportError: # pragma: no cover
    import unittest

class BaseTestCase(unittest.TestCase):
    def read_memory(self, fmt, addr):
        self.fail("unexpected read_memory")

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
                value = int(value, 0)
                frame.f_globals[name] = value
            except:
                raise HeaderFileError(filename, linenumber)

    def run(self, *args, **kwargs):
        saved_env = self.i8ctx.env
        self.i8ctx.env = self
        try:
            return BaseTestCase.run(self, *args, **kwargs)
        finally:
            self.i8ctx.env = saved_env

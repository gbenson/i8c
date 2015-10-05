try:
    import unittest2 as unittest
except ImportError: # pragma: no cover
    import unittest

class BaseTestCase(unittest.TestCase):
    def read_memory(self, fmt, addr):
        self.fail("unexpected read_memory")

class TestCase(BaseTestCase):
    def run(self, *args, **kwargs):
        saved_env = self.i8ctx.env
        self.i8ctx.env = self
        try:
            return BaseTestCase.run(self, *args, **kwargs)
        finally:
            self.i8ctx.env = saved_env

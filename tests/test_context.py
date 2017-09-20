# -*- coding: utf-8 -*-
# Copyright (C) 2017 Red Hat, Inc.
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

from tests import TestCase
from i8c import runtime
import weakref

class ContextTests(object):
    def setUp(self):
        self.ctx = runtime.Context(*self.ctx_init_args)
        self.ctx_ref = weakref.ref(self.ctx)

    def tearDown(self):
        self.ctx.finalize()
        del self.ctx
        self.assertIsNone(self.ctx_ref())

    def test_environment(self):
        """Ensure tests always have a working environment."""
        self.__test_environment()
        self.ctx.finalize()
        self.__test_environment()

    def __test_environment(self):
        self.assertIsNotNone(self.ctx.env)
        self.__assert_ctx_env_immutable()
        if self.ctx.env is not self:
            self.__test_null_environment()

    def __assert_ctx_env_immutable(self):
        saved_env = self.ctx.env
        with self.assertRaises(AttributeError):
            self.ctx.env = 14
        self.assertIs(self.ctx.env, saved_env)

    def __test_null_environment(self):
        with self.assertRaises(AssertionError) as cm:
            self.ctx.env.runTest()
        self.assertEqual(cm.exception.args, ("should not call",))

    def test_override(self):
        """Test Context.override."""
        class FuncWrap(object):
            signature = "test::func(pi)"
            def __init__(self, impl):
                self.impl = impl

        self.__override_testfunc_2_called = False
        self.ctx.override(FuncWrap(self.__override_testfunc_1))
        self.ctx.override(FuncWrap(self.__override_testfunc_2))
        self.assertFalse(self.__override_testfunc_2_called)
        self.ctx.call(FuncWrap.signature, *self.__override_testfunc_args)
        self.assertTrue(self.__override_testfunc_2_called)

    def __override_testfunc_1(self, *args):
        self.fail("Context.override didn't replace the original")

    def __override_testfunc_2(self, *args):
        self.assertEqual(args, self.__override_testfunc_args)
        self.__override_testfunc_2_called = True

    __override_testfunc_args = (0x18273645, 0x71826354)

class TestContext_EnvIsTestCase(ContextTests, TestCase):
    @property
    def ctx_init_args(self):
        return (self,)

class TestContext_EnvIsNone(ContextTests, TestCase):
    ctx_init_args = (None,)

class TestContext_EnvUnspecified(ContextTests, TestCase):
    ctx_init_args = ()

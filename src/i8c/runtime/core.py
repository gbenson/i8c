# -*- coding: utf-8 -*-
# Copyright (C) 2017 Red Hat, Inc.
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

import weakref
try:
    import unittest2 as unittest
except ImportError: # pragma: no cover
    import unittest

__all__ = ("unittest", "TestObject")

class FallbackEnvironment(unittest.TestCase):
    """Dummy environment so TestObject.env.assert* always works."""

    def runTest(self):
        self.fail("should not call")

_fallback_env = FallbackEnvironment()

class TestObject(object):
    """An object weakly associated with a testcase."""

    def __init__(self, env):
        self.__env = weakref.ref(env or _fallback_env)

    @property
    def env(self):
        return self.__env() or _fallback_env

class TempSetAttr(object):
    """Context manager to temporarily set an attribute in an object."""

    __unset = object()

    def __init__(self, object, name, value):
        self.object = object
        self.name = name
        self.value = value

    def __enter__(self):
        self.__saved = getattr(self.object, self.name, self.__unset)
        setattr(self.object, self.name, self.value)

    def __exit__(self, type, value, traceback):
        if type is None:
            if self.__saved is self.__unset:
                delattr(self.object, self.name)
            else:
                setattr(self.object, self.name, self.__saved)

# -*- coding: utf-8 -*-
# Copyright (C) 2015 Red Hat, Inc.
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

from . import names
from . import stack
from . import types
from . import visitors
import copy

class External(stack.Element):
    def __init__(self, name, type):
        if type.basetype is types.PTRTYPE:
            assert name.is_shortname
        else:
            assert type.is_function
            assert name.is_fullname
        stack.Element.__init__(self, type, name)

    @property
    def name(self):
        return self.names[0]

class ExternTable(visitors.Visitable):
    def __init__(self):
        self.entries = {}

    def add(self, name, type):
        key = str(name)
        assert not key in self.entries
        self.entries[key] = External(name, type)

    def lookup(self, name):
        result = self.__lookup(name)
        if result is None and name.is_shortname:
            fullname = name.with_provider(self.default_provider)
            result = self.__lookup(fullname)
        return result

    def __lookup(self, name):
        assert isinstance(name, names.Name)
        return self.entries.get(str(name), None)

class PerFileTableCreator(object):
    def visit_toplevel(self, toplevel):
        toplevel.table = self.table = ExternTable()
        for node in toplevel.functions:
            node.accept(self)

    def visit_function(self, function):
        self.table.add(function.name.value, function.type)

class PerFuncTableCreator(object):
    def visit_toplevel(self, toplevel):
        for node in toplevel.functions:
            self.table = copy.copy(toplevel.table)
            node.accept(self)

    def visit_function(self, function):
        self.table.default_provider = function.name.provider
        function.externals.accept(self)
        function.externals = self.table

    def visit_externals(self, externals):
        for node in externals.children:
            node.accept(self)

    def visit_external(self, external):
        self.table.add(external.name.value, external.typename.type)

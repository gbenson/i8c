# -*- coding: utf-8 -*-
# Copyright (C) 2015-16 Red Hat, Inc.
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

from . import RedefinedIdentError
from . import names
from . import parser
from . import stack
from . import types
from . import visitors
from . import warn
import copy

class External(stack.Element):
    def __init__(self, name, type, ast):
        if type.basetype is types.PTRTYPE:
            assert name.is_shortname
        else:
            assert type.is_function
            assert name.is_fullname
        stack.Element.__init__(self, type, name)
        self.ast = ast

    @property
    def name(self):
        return self.names[0]

class PlaceHolder(object):
    def __init__(self, name):
        self.name = name

class ExternTable(visitors.Visitable):
    def __init__(self):
        self.default_provider = None
        self.entries = {}

    def add(self, node, type):
        """Add an entry to the table."""
        self.__add(node, External, type, node)

    def block(self, node):
        """Reserve a name in the table."""
        self.__add(node, PlaceHolder)

    def __add(self, node, klass, *args):
        entry = klass(node.name.value, *args)
        key = str(entry.name)

        prev = entry.name
        if prev.is_fullname and prev.provider == self.default_provider:
            prev = prev.without_provider()
        prev = self.__lookup(prev)
        if prev is not None:
            if (isinstance(entry, External)
                  and isinstance(prev, External)
                  and entry.type.encoding == prev.type.encoding):
                if not isinstance(entry.ast, parser.Function):
                    warn("unnecessary definition of ‘%s’" % entry.name,
                         entry.name)
                    warn("‘%s’ was first defined here" % prev.name,
                         prev.name)
                return
            raise RedefinedIdentError(entry.name, "name", key, prev.name)

        self.entries[key] = entry

    def lookup(self, name):
        result = self.__lookup(name)
        if isinstance(result, PlaceHolder):
            result = None
        return result

    def __lookup(self, name):
        result = self.__lookup_one(name)
        if result is None and name.is_shortname:
            fullname = name.with_provider(self.default_provider)
            result = self.__lookup_one(fullname)
        return result

    def __lookup_one(self, name):
        assert isinstance(name, names.Name)
        return self.entries.get(str(name), None)

class TableCreator(object):
    def visit_external(self, external):
        self.table.add(external, external.typename.type)

class PerFileTableCreator(TableCreator):
    def visit_toplevel(self, toplevel):
        toplevel.table = self.table = ExternTable()
        for node in toplevel.children:
            node.accept(self)

    def visit_function(self, function):
        self.table.add(function, function.type)

    def visit_wordsize(self, wordsize):
        pass

    def visit_typedef(self, typedef):
        pass

class PerFuncTableCreator(TableCreator):
    def visit_toplevel(self, toplevel):
        for node in toplevel.functions:
            self.table = copy.copy(toplevel.table)
            self.table.entries = copy.copy(self.table.entries)
            node.accept(self)

    def visit_function(self, function):
        for node in function.children:
            node.accept(self)
        function.externals = self.table

    def visit_fullname(self, name):
        self.table.default_provider = name.provider

    def visit_parameters(self, parameters):
        for node in parameters.children:
            node.accept(self)

    def visit_parameter(self, parameter):
        self.table.block(parameter)

    def visit_returntypes(self, returntypes):
        pass

    def visit_externals(self, externals):
        for node in externals.children:
            node.accept(self)

    def visit_operations(self, ops):
        pass


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

from . import NameAnnotatorError

class Name(object):
    def __init__(self, provider, name):
        assert provider is None or provider
        assert name
        self.provider = provider
        self.name = name

    @property
    def is_shortname(self):
        return self.provider is None

    @property
    def is_fullname(self):
        return not self.is_shortname

    def with_provider(self, provider):
        assert self.is_shortname
        return Name(provider, self.name)

    def without_provider(self, provider):
        assert self.is_fullname
        assert provider == self.provider
        return Name(None, self.name)

    def __eq__(self, other): # pragma: no cover
        # This comparison is excluded from coverage because it's
        # not currently entered (but it must be defined because
        # we've defined __ne__ below).
        return not (self != other)

    def __ne__(self, other):
        return (other is None
                or self.provider != other.provider
                or self.name != other.name)

    def __str__(self):
        if self.provider is not None:
            return "%s::%s" % (self.provider, self.name)
        else:
            return self.name

class NameAnnotator(object):
    def visit_toplevel(self, toplevel):
        for node in toplevel.functions:
            node.accept(self)

    def visit_function(self, function):
        function.name.accept(self)
        self.check_provider(function.name)
        for node in function.entry_stack:
            node.accept(self)
        function.operations.accept(self)

    def visit_parameters(self, parameters):
        for node in parameters.children:
            node.accept(self)

    def visit_parameter(self, parameter):
        parameter.name.accept(self)

    def visit_externals(self, externals):
        for node in externals.children:
            node.accept(self)

    def visit_external(self, external):
        external.name.accept(self)

    def visit_operations(self, ops):
        for node in ops.named_operations:
            node.accept(self)

    def visit_castop(self, op):
        for node in op.named_operands:
            node.accept(self)

    def visit_loadop(self, op):
        for node in op.named_operands:
            node.accept(self)

    def visit_nameop(self, op):
        op.name.accept(self)

    def visit_fullname(self, name):
        name.value = Name(name.provider, name.shortname)

    def visit_shortname(self, name):
        name.value = Name(None, name.name)

    def check_provider(self, name):
        provider = name.value.provider
        if provider.startswith("i8"):
            raise NameAnnotatorError(
                name, "provider ‘%s’ is reserved" % provider)

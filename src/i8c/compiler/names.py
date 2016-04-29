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

from . import logger
from . import ParserError
from . import ReservedIdentError

debug_print = logger.debug_printer_for(__name__)

class Name(object):
    is_builtin = False

    def __init__(self, ast, provider, name):
        assert provider is None or provider
        assert name
        self.ast = ast
        self.provider = provider
        self.name = name

    @property
    def fileline(self):
        return self.ast.fileline

    @property
    def is_shortname(self):
        return self.provider is None

    @property
    def is_fullname(self):
        return not self.is_shortname

    def with_provider(self, provider):
        assert self.is_shortname
        return Name(self.ast, provider, self.name)

    def without_provider(self):
        assert self.is_fullname
        return Name(self.ast, None, self.name)

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
        for node in toplevel.children:
            self.function = None
            node.accept(self)

    def visit_wordsize(self, wordsize):
        pass

    def visit_typedef(self, typedef):
        pass

    def visit_function(self, function):
        if function.provider.startswith("i8"):
            raise ReservedIdentError(
                function, "provider", function.provider)
        self.function = function

        self.allow_shortname = False
        self.allow_fullname = True
        for node in function.children:
            node.accept(self)

        if debug_print.is_enabled:
            debug_print("%s\n\n" % function)

    def visit_parameters(self, parameters):
        self.allow_shortname = True
        self.allow_fullname = False

        for node in parameters.children:
            node.accept(self)

    def visit_parameter(self, parameter):
        parameter.name.accept(self)

    def visit_externals(self, externals):
        for node in externals.children:
            node.accept(self)

    def visit_external(self, external):
        if external.typename.type.is_function:
            self.allow_shortname = False
            self.allow_fullname = True
        else:
            self.allow_shortname = True
            self.allow_fullname = False

        external.name.accept(self)

    def visit_returntypes(self, returntypes):
        pass

    def visit_operations(self, ops):
        self.allow_shortname = True
        self.allow_fullname = True

        for node in ops.children:
            node.accept(self)

    def visit_label(self, label):
        pass

    def visit_operation(self, op):
        pass

    def visit_loadop(self, op):
        for node in op.named_operands:
            node.accept(self)

    def visit_namecastop(self, op):
        for node in op.named_operands:
            node.accept(self)

    # Visitors for names

    def visit_fullname(self, node):
        if not self.allow_fullname:
            raise ParserError(node.tokens[1:])
        node.value = Name(node, node.provider, node.shortname)

    def visit_shortname(self, node):
        if self.allow_shortname:
            provider = None
        elif self.allow_fullname and self.function is not None:
            provider = self.function.provider
        else:
            raise ParserError(node.tokens)
        node.value = Name(node, provider, node.name)

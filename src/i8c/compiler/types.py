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

from .. import constants
from . import TypeAnnotatorError
from . import logger

debug_print = logger.debug_printer_for(__name__)

class Type(object):
    """Base class for all types.
    """
    def __init__(self, name):
        self.name = name

    def lowest_common_ancestor(self, other):
        last = None
        for type1, type2 in zip(self.__lca_path(), other.__lca_path()):
            if type1 is not type2:
                break
            last = type1
        return last

    def __lca_path(self):
        parent = self.basetype
        if parent == self:
            return (self,)
        return self.parent.__lca_path() + (self,)

class BaseType(Type):
    """Base class for types that are not an alias for some other type.
    """
    @property
    def basetype(self):
        return self

    @property
    def sizedtype(self):
        return None

class CoreType(BaseType):
    """The three core types: int, ptr and opaque.
    """
    class_init_complete = False
    is_function = False

    def __init__(self, name, encoding, is_computable):
        assert not CoreType.class_init_complete
        BaseType.__init__(self, name)
        self.encoding = encoding
        self.is_computable = is_computable

class FuncType(BaseType):
    """Function types.
    """
    is_computable = False
    is_function = True

    def __init__(self, functype):
        functype.paramtypes.accept(self)
        functype.returntypes.accept(self)
        ptypes = ", ".join((type.name for type in self.paramtypes))
        rtypes = ", ".join((type.name for type in self.returntypes))
        name = "func"
        if rtypes:
            name += " " + rtypes
        name += " (%s)" % ptypes
        Type.__init__(self, name)

    @property
    def encoding(self):
        return "%s%s(%s)" % (
            constants.I8_TYPE_FUNC,
            "".join((type.encoding for type in self.returntypes)),
            "".join((type.encoding for type in self.paramtypes)))

    def __eq__(self, other):
        return not (self != other)

    def __ne__(self, other):
        return (not isinstance(other, FuncType)
                or self.paramtypes != other.paramtypes
                or self.returntypes != other.returntypes)

    def visit_paramtypes(self, paramtypes):
        self.__list = self.paramtypes = []
        for node in paramtypes.children:
            node.accept(self)
        del self.__list

    def visit_returntypes(self, returntypes):
        self.__list = self.returntypes = []
        for node in returntypes.children:
            node.accept(self)
        del self.__list

    def visit_basictype(self, basictype):
        self.__list.append(basictype.type)

    def visit_functype(self, functype):
        self.__list.append(functype.type)

class AliasType(Type):
    """A type that is an alias for some other type.
    """
    def __init__(self, name, parent):
        assert parent is not None
        Type.__init__(self, name)
        self.parent = parent

    @property
    def basetype(self):
        return self.parent.basetype

    @property
    def sizedtype(self):
        return self.parent.sizedtype

    @property
    def is_computable(self):
        return self.parent.is_computable

    @property
    def is_function(self):
        return self.parent.is_function

    @property
    def encoding(self):
        return self.parent.encoding

class SizedType(AliasType):
    """The sized-integer types used by "deref".
    """
    class_init_complete = False

    def __init__(self, size_bytes, is_signed):
        assert not SizedType.class_init_complete
        name = "%s%d" % (is_signed and "s" or "u", size_bytes << 3)
        AliasType.__init__(self, name, INTTYPE)
        self.size_bytes = size_bytes
        self.is_signed = is_signed

    @property
    def sizedtype(self):
        return self

def __create_builtin_types():
    """Create the builtin types INTTYPE, PTRTYPE, etc.
    """
    def add_builtin_type(type):
        globals()[type.name.upper() + "TYPE"] = type
    for name in ("int", "ptr", "opaque"):
        code = getattr(constants, "I8_TYPE_" + name[:3].upper())
        add_builtin_type(CoreType(name, code, name != "opaque"))
    CoreType.class_init_complete = True
    add_builtin_type(AliasType("bool", INTTYPE))
    for is_signed in range(2):
        for shift in range(4):
            size = 1 << shift
            add_builtin_type(SizedType(size, is_signed))
    SizedType.class_init_complete = True
__create_builtin_types()

class TypeAnnotator(object):
    def visit_toplevel(self, toplevel):
        self.types = {}
        for name, type in globals().items():
            if name.endswith("TYPE"):
                self.add_type(type)
        self.in_toplevel = True
        for node in toplevel.children:
            node.accept(self)
        assert self.in_toplevel

    def add_type(self, type, node=None):
        if type.name in self.types:
            raise TypeAnnotatorError(
                node, "type ‘%s’ already exists" % type.name)
        self.types[type.name] = type

    def get_type(self, basictype):
        name = basictype.name
        result = self.types.get(name, None)
        if result is None:
            raise TypeAnnotatorError(
                basictype, "undefined type ‘%s’" % name)
        return result

    def visit_basictype(self, basictype):
        if self.in_toplevel:
            self.add_basictype(basictype)
        else:
            self.annotate_basictype(basictype)

    def visit_functype(self, functype):
        if self.in_toplevel:
            self.add_functype(functype)
        else:
            self.annotate_functype(functype)

    # Process "define type" statements

    def visit_typedef(self, typedef):
        self.newtype = None
        for node in typedef.children:
            node.accept(self)

    def visit_typename(self, typename):
        assert self.newtype is None
        self.newtype = typename

    def add_basictype(self, basictype):
        assert self.newtype is not None
        parent = self.get_type(basictype)
        self.add_type(AliasType(self.newtype.name, parent), self.newtype)

    def __annotate_functype(self, functype):
        saved = self.in_toplevel
        try:
            self.in_toplevel = False
            functype.paramtypes.accept(self)
            functype.returntypes.accept(self)
        finally:
            self.in_toplevel = saved

    def add_functype(self, functype):
        assert self.newtype is not None
        self.__annotate_functype(functype)
        parent = FuncType(functype)
        self.add_type(AliasType(self.newtype.name, parent), self.newtype)

    # Add "type" fields where necessary in function definitions

    def visit_function(self, function):
        toplevel_types = self.types
        self.types = self.types.copy()
        self.in_toplevel = False

        for node in function.children:
            node.accept(self)

        if debug_print.is_enabled:
            debug_print("%s\n\n" % function)

        self.types = toplevel_types
        self.in_toplevel = True

    def visit_fullname(self, fullname):
        pass

    def visit_returntypes(self, returntypes):
        for node in returntypes.children:
            node.accept(self)

    def visit_paramtypes(self, paramtypes):
        for node in paramtypes.children:
            node.accept(self)

    def visit_parameters(self, parameters):
        for node in parameters.children:
            node.accept(self)

    def visit_parameter(self, parameter):
        parameter.typename.accept(self)

    def visit_externals(self, externals):
        for node in externals.children:
            node.accept(self)

    def visit_external(self, external):
        external.typename.accept(self)

    def annotate_basictype(self, basictype):
        basictype.type = self.get_type(basictype)

    def annotate_functype(self, functype):
        self.__annotate_functype(functype)
        functype.type = FuncType(functype)

    def visit_operations(self, ops):
        for node in ops.typed_operations:
            node.accept(self)

    def visit_castop(self, op):
        op.typename.accept(self)

    def visit_derefop(self, op):
        for node in op.children:
            node.accept(self)

    def visit_loadop(self, op):
        for node in op.typed_operands:
            node.accept(self)

    def visit_integer(self, constant):
        constant.type = INTTYPE

    def visit_pointer(self, constant):
        constant.type = PTRTYPE

    def visit_boolean(self, constant):
        constant.type = BOOLTYPE

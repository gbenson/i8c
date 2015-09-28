from i8c.exceptions import TypeAnnotatorError

class Type(object):
    """Base class for all types.
    """
    def __init__(self, name):
        self.name = name

class RootType(Type):
    """Base class for types that are not an alias for some other type.
    """
    @property
    def basetype(self):
        return self

    @property
    def sizedtype(self):
        return None

    @property
    def is_computable(self):
        return self in (INTTYPE, PTRTYPE)

class AliasType(Type):
    """Base class for types that are aliases for some other type.
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
    def encoding(self):
        return self.parent.encoding

class CoreType(RootType):
    @property
    def encoding(self):
        return self.name[0]

class FuncType(RootType):
    def __init__(self, functype):
        functype.paramtypes.accept(self)
        functype.returntypes.accept(self)
        Type.__init__(self, "function %s (%s)" % (
            ", ".join((type.name for type in self.returntypes)),
            ", ".join((type.name for type in self.paramtypes))))

    @property
    def encoding(self):
        return "F%s(%s)" % (
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

class SizedType(AliasType):
    def __init__(self, size_bytes, is_signed):
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
        add_builtin_type(CoreType(name))
    add_builtin_type(AliasType("bool", INTTYPE))
    for is_signed in range(2):
        for shift in range(4):
            size = 1 << shift
            add_builtin_type(SizedType(size, is_signed))
__create_builtin_types()

def __lca_path(type):
    if hasattr(type, "parent"):
        parents = __lca_path(type.parent)
    else:
        parents = ()
    return parents + (type,)

def lowest_common_ancestor(type1, type2):
    last = None
    for type1, type2 in zip(*map(__lca_path, (type1, type2))):
        if type1 is not type2:
            break
        last = type1
    return last

class TypeAnnotator(object):
    def visit_toplevel(self, toplevel):
        self.types = {}
        map(self.add_type,
            (type
             for name, type in globals().items()
             if name.endswith("TYPE")))
        self.in_toplevel = True
        for node in toplevel.children:
            node.accept(self)
        assert self.in_toplevel

    def add_type(self, type, node=None):
        if self.types.has_key(type.name):
            raise TypeAnnotatorError(
                node, "type `%s' already exists" % type.name)
        self.types[type.name] = type

    def get_type(self, basictype):
        name = basictype.name
        result = self.types.get(name, None)
        if result is None:
            raise TypeAnnotatorError(
                basictype, "undefined type `%s'" % name)
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

    def visit_funcref(self, funcref):
        funcref.typename.accept(self)

    def visit_symref(self, symref):
        symref.typename.accept(self)

    def annotate_basictype(self, basictype):
        basictype.type = self.get_type(basictype)

    def annotate_functype(self, functype):
        self.__annotate_functype(functype)
        functype.type = FuncType(functype)

    def visit_operations(self, ops):
        for node in ops.typed_operations:
            node.accept(self)

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

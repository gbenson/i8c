from i8c.exceptions import NameAnnotatorError

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

    def __eq__(self, other):
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
        self.ensure_unreserved(function)
        self.function_provider = function.name.value.provider
        for node in function.entry_stack:
            node.accept(self)
        function.operations.accept(self)

    def visit_parameters(self, parameters):
        self.default_provider = None
        for node in parameters.children:
            node.accept(self)

    def visit_parameter(self, parameter):
        parameter.name.accept(self)

    def visit_externals(self, externals):
        for node in externals.children:
            node.accept(self)

    def visit_funcref(self, funcref):
        self.default_provider = self.function_provider
        funcref.name.accept(self)

    def visit_symref(self, symref):
        self.default_provider = None
        symref.name.accept(self)

    def visit_operations(self, ops):
        self.default_provider = None
        for node in ops.named_operations:
            node.accept(self)

    def visit_loadop(self, op):
        for node in op.named_operands:
            node.accept(self)

    def visit_nameop(self, op):
        op.name.accept(self)

    def visit_fullname(self, name):
        name.value = Name(name.provider, name.shortname)

    def visit_shortname(self, name):
        name.value = Name(self.default_provider, name.name)

    def ensure_unreserved(self, item):
        provider = item.name.value.provider
        if provider.startswith("i8"):
            raise NameAnnotatorError(
                item.name, "provider `%s' is reserved" % provider)

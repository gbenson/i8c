# -*- coding: utf-8 -*-
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

    def visit_funcref(self, funcref):
        funcref.name.accept(self)

    def visit_symref(self, symref):
        symref.name.accept(self)

    def visit_operations(self, ops):
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
        name.value = Name(None, name.name)

    def check_provider(self, name):
        provider = name.value.provider
        if provider.startswith("i8"):
            raise NameAnnotatorError(
                name, u"provider ‘%s’ is reserved" % provider)

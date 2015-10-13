from . import *
from . import elffile
from . import functions
from . import stack

class Context(object):
    def __init__(self):
        self.functions = {}
        self.env = None
        self.wordsize = None
        self.tracelevel = 0
        self.__last_traced = None

    # Methods to XXX

    def register_function(self, function):
        funclist = self.functions.get(function.signature, [])
        if not funclist:
            self.functions[function.signature] = funclist
        funclist.append(function)

    def get_function(self, sig_or_ref):
        if isinstance(sig_or_ref, functions.UnresolvedFunction):
            reference = sig_or_ref
            signature = reference.signature
        else:
            assert isinstance(sig_or_ref, str)
            signature = sig_or_ref
            reference = None
        # First check the registered functions
        funclist = self.functions.get(signature, None)
        if funclist is not None:
            if len(funclist) == 1:
                return funclist[0]
            elif len(funclist) > 1:
                raise AmbiguousFunctionError(sig_or_ref)
        # No registered function with this name
        if reference is not None:
            impl = "call_%s_%s" % (reference.provider, reference.name)
            impl = getattr(self.env, impl, None)
            if impl is not None:
                return functions.BuiltinFunction(reference, impl)
        raise UndefinedFunctionError(sig_or_ref)

    # Methods to XXX

    def import_notes(self, filename):
        ef = elffile.open(filename)
        if self.wordsize is None or self.wordsize < ef.wordsize:
            self.wordsize = ef.wordsize
        for note in ef.infinity_notes:
            self.register_function(functions.BytecodeFunction(note))

    def new_stack(self):
        return stack.Stack(self.wordsize)

    def call(self, signature, *args):
        function = self.get_function(signature)
        stack = self.new_stack()
        stack.push_multi(function.ptypes, args)
        function.execute(self, stack)
        return stack.pop_multi(function.rtypes)

    def __trace(self, (function, pc), stack, encoded, decoded):
        if self.tracelevel > 0:
            if function != self.__last_traced:
                print "\n%s:" % function
                self.__last_traced = function
            if self.tracelevel > 1:
                stack.trace(self.tracelevel)
            print "  %04x: %-12s %s" % (pc, encoded, decoded)

    def trace_operation(self, *args):
        self.__trace(*args)

    def trace_call(self, function, stack):
        if not isinstance(function, functions.BytecodeFunction):
            if self.tracelevel > 0:
                print "\n%s:" % function
                print "  NON-BYTECODE FUNCTION"
        self.__last_traced = None

    def trace_return(self, location, stack):
        self.__trace(location, stack, "", "RETURN")
        self.__last_traced = None

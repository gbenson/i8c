# -*- coding: utf-8 -*-
from i8c.exceptions import ParsedError, StackError, StackTypeError
from i8c import logger
from i8c import names
from i8c import types
import copy

debug_print = logger.debug_printer_for(__name__)

class Stack(object):
    def __init__(self, funcname):
        assert isinstance(funcname, names.Name)
        assert funcname.provider is not None
        self.funcprovider = funcname.provider
        self.slots = []
        self.is_mutable = True
        self.max_depth = 0

    def push(self, item):
        assert self.is_mutable
        self.slots.insert(0, item)
        self.max_depth = max(self.max_depth, len(self.slots))

    def pop(self):
        assert self.is_mutable
        self.__assert_depth(1)
        return self.slots.pop(0)

    def name_slot(self, index, name):
        assert self.is_mutable
        assert name is None or isinstance(name, names.Name)
        self.__assert_depth(index)
        value = copy.copy(self.slots[index])
        value.names = copy.copy(value.names)
        value.names.append(name)
        self.slots[index] = value

    def indexes_for(self, name):
        assert isinstance(name, names.Name)
        # Set search to either
        #   shortname, funcprovider::shortname
        # or
        #   otherprovider::shortname
        if name.is_fullname and name.provider == self.funcprovider:
            search = [name.without_provider(self.funcprovider), name]
        elif name.is_shortname:
            search = [name, name.with_provider(self.funcprovider)]
        else:
            search = [name]
        results = []
        for value, index in zip(self.slots, xrange(len(self.slots))):
            # Does this slot match the names we're looking for?
            if not self.__names_match(search, value.names):
                continue
            # Is this slot just a copy of a previous result?
            if value in (self.slots[result] for result in results):
                continue
            # This is a new match
            results.append(index)
        return results

    def __names_match(self, list1, list2):
        for name1 in list1:
            for name2 in list2:
                if name1 == name2:
                    return True
        return False

    def make_immutable(self):
        self.is_mutable = False

    def mutable_copy(self):
        assert not self.is_mutable
        # Don't use deepcopy.  We want to copy the slots list
        # but copying values is wasteful (we don't need it)
        # and copying value types is problematic as it breaks
        # "is" comparison.
        result = copy.copy(self)
        result.slots = copy.copy(self.slots)
        result.is_mutable = True
        return result

    def __assert_depth(self, depth):
        if len(self.slots) < depth:
            raise StackError(self.current_op, None, "stack underflow")

    def __getitem__(self, index):
        self.__assert_depth(index)
        return self.slots[index]

    def __str__(self):
        if not self.slots:
            return "   <empty stack>"
        return "\n".join(("%4d: %s" % (slot, self[slot])
                          for slot in xrange(len(self.slots))))

class Value:
    @staticmethod
    def computed(type):
        """A value that was computed.
        """
        return Value(type, None, None)

    @staticmethod
    def from_ast_constant(const):
        """A value created from a constant in the AST.
        """
        return Value(const.type, None, const.value)

    @staticmethod
    def from_ast_parameter(param):
        """A value created from a parameter in the AST.
        """
        return Value(param.typename.type, param.name.value, None)

    def __init__(self, thetype, name, value):
        assert thetype is not None
        assert isinstance(thetype, types.Type)
        self.type = thetype
        self.names = []
        if name is not None:
            assert isinstance(name, names.Name)
            self.names.append(name)
        if value is not None:
            assert isinstance(value, (int, long))
        self.value = value

    @property
    def basetype(self):
        return self.type.basetype

    def __str__(self):
        result = ""
        if not self.names:
            result += "anonymous "
        result += self.type.name
        if self.names:
            result += " "
            if len(self.names) > 1:
                result += "["
            result += ", ".join(map(str, self.names))
            if len(self.names) > 1:
                result += "]"
        if self.value is not None:
            result += " = %d" % self.value
        return result

class StackWalker(object):
    def visit_toplevel(self, toplevel):
        for node in toplevel.functions:
            node.accept(self)

    def visit_function(self, function):
        # Build the entry stack
        self.entry_stack = Stack(function.name.value)
        for node in function.entry_stack:
            node.accept(self)
        self.entry_stack.make_immutable()
        # Build the return types
        self.returntypes = []
        function.returntypes.accept(self)
        # Walk the operations
        self.max_stack = 0
        self.__enter_block(function.entry_block, None, self.entry_stack)
        function.max_stack = self.max_stack

    # Build the entry stack

    def visit_parameters(self, parameters):
        self.__visit_entry_slots(parameters)

    def visit_parameter(self, param):
        self.__visit_entry_slot(param)

    def visit_externals(self, externals):
        self.__visit_entry_slots(externals)

    def visit_funcref(self, funcref):
        self.__visit_entry_slot(funcref)

    def visit_symref(self, symref):
        self.__visit_entry_slot(symref)

    def __visit_entry_slots(self, parameters):
        for node in parameters.children:
            node.accept(self)

    def __visit_entry_slot(self, param):
        self.entry_stack.push(Value.from_ast_parameter(param))

    # Build the return types

    def visit_returntypes(self, returntypes):
        for node in returntypes.children:
            node.accept(self)

    def visit_basictype(self, basictype):
        self.returntypes.append(basictype.type)

    def visit_functype(self, functype):
        self.returntypes.append(functype.type)

    # Manage transitions between blocks

    def __enter_block(self, block, from_block, new_entry_stack):
        self.__current_block = block
        if not hasattr(block, "entry_stacks"):
            # First entry to BLOCK
            block.entry_stacks = {}
        old_entry_stack = block.entry_stacks.get(from_block, None)
        if old_entry_stack is None:
            # First entry to BLOCK from FROM_BLOCK
            block.entry_stacks[from_block] = new_entry_stack
        else:
            # XXX return if nothing changed
            # XXX the below is a temporary hack
            if old_entry_stack is new_entry_stack:
                return
            raise NotImplementedError
        if len(block.entry_stacks) != 1:
            raise NotImplementedError
        assert not hasattr(block, "entry_stack") # XXX
        block.entry_stack = new_entry_stack
        block.accept(self)

    def __leave_block(self):
        from_block = self.__current_block
        stack = self.stack
        del self.__current_block, self.stack
        stack.make_immutable()
        self.max_stack = max(self.max_stack, stack.max_depth)
        for block in from_block.exits:
            self.__enter_block(block, from_block, stack)

    # Walk the operations

    def visit_basicblock(self, block):
        self.stack = block.entry_stack.mutable_copy()
        debug_print("%s (%s):\n\n%s\n" % (
            block.name, block.fileline, self.stack))
        for op in block.ops:
            debug_print("\n %s\n\n" % op)
            self.stack.current_op = op
            op.accept(self)
            if hasattr(self, "stack"):
                debug_print("%s\n" % self.stack)

    def visit_addop(self, op):
        # Check the types before mutating the stack
        # so any error messages show the whole setup
        fulltypes = [self.stack[index].type for index in (0, 1)]
        basetypes = [type.basetype for type in fulltypes]
        # At least one of the operands must be INTTYPE
        if types.INTTYPE not in basetypes:
            raise StackTypeError(op, self.stack)
        if types.PTRTYPE in basetypes:
            rtype = types.PTRTYPE
        else:
            rtype = types.lowest_common_ancestor(*fulltypes)
            if rtype is None:
                # One of the types was not INTTYPE
                raise StackTypeError(op, self.stack)
        # Now pop everything and push the result
        self.stack.pop()
        self.stack.pop()
        self.stack.push(Value.computed(rtype))

    def visit_branchop(self, op):
        assert self.stack[0].type is types.BOOLTYPE
        self.stack.pop()
        self.__leave_block()

    # and, div, mod, mul, or, shl, shr, shra, xor
    def visit_binaryop(self, op):
        # Check the types before mutating the stack
        # so any error messages show the whole setup
        fulltypes = [self.stack[index].type for index in (0, 1)]
        basetypes = [type.basetype for type in fulltypes]
        if basetypes != [types.INTTYPE, types.INTTYPE]:
            raise StackTypeError(op, self.stack)
        rtype = types.lowest_common_ancestor(*fulltypes)
        assert rtype is not None
        self.stack.pop()
        self.stack.pop()
        self.stack.push(Value.computed(rtype))

    def visit_callop(self, op):
        # Check the types before mutating the stack
        # so any error messages show the whole setup
        ftype = self.stack[0].basetype
        if not isinstance(ftype, types.FuncType):
            raise StackError(op, self.stack, "stack[0] not a function:")
        num_params = len(ftype.paramtypes)
        for pindex in xrange(num_params):
            sindex = num_params - pindex
            ptype = ftype.paramtypes[pindex]
            stype = self.stack[sindex].type
            if stype != ptype:
                raise StackError(op, self.stack,
                                 "wrong type in stack[%d]" % sindex)
        # Now pop everything and push the result
        for i in xrange(1 + num_params):
            self.stack.pop()
        num_returns = len(ftype.returntypes)
        for sindex in xrange(num_returns):
            rindex = num_returns - sindex - 1
            self.stack.push(Value.computed(ftype.returntypes[rindex]))

    def visit_compareop(self, op):
        # Check the types before mutating the stack
        # so any error messages show the whole setup
        typea = self.stack[0].type
        typeb = self.stack[1].type
        for type in typea, typeb:
            if not type.is_computable:
                raise StackTypeError(op, self.stack)
        if typea.basetype is not typeb.basetype:
            raise StackTypeError(op, self.stack)
        # Now pop everything and push the result
        self.stack.pop()
        self.stack.pop()
        self.stack.push(Value.computed(types.BOOLTYPE))

    def visit_constop(self, op):
        self.stack.push(Value.from_ast_constant(op))

    def visit_derefop(self, op):
        rtype = op.type
        if not rtype.is_computable:
            raise ParsedError(
                op, u"can't dereference to ‘%s’" % rtype.name)
        # Check the types before mutating the stack
        # so any error messages show the whole setup
        type = self.stack[0].type
        if not type.basetype is types.PTRTYPE:
            raise StackTypeError(op, self.stack)
        self.stack.pop()
        self.stack.push(Value.computed(rtype))

    def visit_dropop(self, op):
        self.stack.pop()

    def visit_dupop(self, op):
        self.stack.push(self.stack[0])

    def visit_gotoop(self, op):
        self.__leave_block()

    def visit_nameop(self, op):
        indexes = self.stack.indexes_for(op.name)
        if indexes:
            if indexes[0] == op.slot:
                return # first result already has this name
            raise StackError(op, self.stack,
                             u"declaration shadows slot %s" % (
                                 ", ".join(map(str, indexes))))
        self.stack.name_slot(op.slot, op.name)

    def visit_overop(self, op):
        self.stack.push(self.stack[1])

    def visit_pickop(self, op):
        self.__pick_op = op
        op.operand.accept(self)
        del self.__pick_op
        op.slot = self.__pick_index
        del self.__pick_index
        self.stack.push(self.stack[op.slot])

    def __pick_by_slot(self, slot):
        self.__pick_index = slot

    def __pick_by_name(self, name):
        indexes = self.stack.indexes_for(name)
        if not indexes:
            raise StackError(self.__pick_op, self.stack,
                             u"no slot matches ‘%s’" % name)
        elif len(indexes) != 1:
            raise StackError(self.__pick_op, self.stack,
                             u"multiple slots match ‘%s’" % name)
        else:
            self.__pick_index = indexes[0]

    def visit_subop(self, op):
        # Check the types before mutating the stack
        # so any error messages show the whole setup
        fulltypes = [self.stack[index].type for index in (0, 1)]
        basetypes = [type.basetype for type in fulltypes]
        if basetypes == [types.INTTYPE, types.PTRTYPE]:
            rtype = types.PTRTYPE
        elif basetypes == [types.INTTYPE, types.INTTYPE]:
            rtype = types.lowest_common_ancestor(*fulltypes)
            assert rtype is not None
        else:
            raise StackTypeError(op, self.stack)
        self.stack.pop()
        self.stack.pop()
        self.stack.push(Value.computed(rtype))

    def visit_returnop(self, op):
        num_returns = len(self.returntypes)
        for index in xrange(num_returns):
            rtype = self.returntypes[index].basetype
            stype = self.stack[index].basetype
            if rtype != stype:
                raise StackError(op, self.stack,
                                 "wrong type in stack[%d]" % index)
        self.__leave_block()

    def visit_rotop(self, op):
        a = self.stack.pop()
        b = self.stack.pop()
        c = self.stack.pop()
        self.stack.push(a)
        self.stack.push(c)
        self.stack.push(b)

    # abs, neg, not
    def visit_unaryop(self, op):
        # Check the types before mutating the stack
        # so any error messages show the whole setup
        if self.stack[0].basetype is not types.INTTYPE:
            raise StackTypeError(op, self.stack)
        a = self.stack.pop()
        self.stack.push(Value.computed(a.type))

    def visit_swapop(self, op):
        a = self.stack.pop()
        b = self.stack.pop()
        self.stack.push(a)
        self.stack.push(b)

    # Visitors for visit_pickop

    def visit_fullname(self, name):
        self.__pick_by_name(name.value)

    def visit_shortname(self, name):
        self.__pick_by_name(name.value)

    def visit_stackslot(self, slot):
        self.__pick_by_slot(slot.value)

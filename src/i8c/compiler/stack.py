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

from ..compat import integer
from . import ParsedError
from . import logger
from . import names
from . import StackError
from . import StackMergeError
from . import StackTypeError
from .types import Type, INTTYPE, PTRTYPE, BOOLTYPE
import copy

debug_print = logger.debug_printer_for(__name__)

class Stack(object):
    def __init__(self, funcname):
        assert isinstance(funcname, names.Name)
        assert funcname.provider is not None
        self.funcname = funcname
        self.slots = []
        self.is_mutable = True
        self.max_depth = 0

    @property
    def depth(self):
        return len(self.slots)

    def push(self, elem):
        assert self.is_mutable
        assert isinstance(elem, Element)
        self.slots.insert(0, elem)
        self.max_depth = max(self.max_depth, self.depth)

    def __push_back(self, item):
        assert self.is_mutable
        self.slots.append(item)
        self.max_depth = max(self.max_depth, self.depth)

    def pop(self):
        assert self.is_mutable
        self.underflow_check(1)
        return self.slots.pop(0)

    def name_slot(self, index, name):
        assert self.is_mutable
        assert name is None or isinstance(name, names.Name)
        self.underflow_check(index)
        elem = copy.copy(self.slots[index])
        elem.names = copy.copy(elem.names)
        elem.names.append(name)
        self.slots[index] = elem

    def cast_slot(self, index, type):
        assert self.is_mutable
        assert isinstance(type, Type)
        self.underflow_check(index)
        elem = copy.copy(self.slots[index])
        elem.type = type
        self.slots[index] = elem

    def indexes_for(self, name):
        assert isinstance(name, names.Name)
        ourprovider = self.funcname.provider
        # Set search to either
        #   shortname, ourprovider::shortname
        # or
        #   otherprovider::shortname
        if name.is_fullname and name.provider == ourprovider:
            search = [name.without_provider(ourprovider), name]
        elif name.is_shortname:
            search = [name, name.with_provider(ourprovider)]
        else:
            search = [name]
        results = []
        for elem, index in zip(self.slots, range(self.depth)):
            # Does this slot match the names we're looking for?
            if not self.__names_match(search, elem.names):
                continue
            # Is this slot just a copy of a previous result?
            if elem in (self.slots[result] for result in results):
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
        # but copying elements is wasteful (we don't need it)
        # and copying element types is problematic as it breaks
        # "is" comparison.
        result = copy.copy(self)
        result.slots = copy.copy(self.slots)
        result.is_mutable = True
        return result

    def underflow_check(self, depth):
        if self.depth < depth:
            raise StackError(self.current_op, None, "stack underflow")

    def __getitem__(self, index):
        self.underflow_check(index)
        return self.slots[index]

    def __str__(self):
        if not self.slots:
            return "   <empty stack>"
        return "\n".join(("%4d: %s" % (slot, self[slot])
                          for slot in range(self.depth)))

    def merge_into(self, previous, ops):
        # There is a direction to this.  We (self) are a new stack
        # joining anoterh, previously processed stack.  If no merge
        # is necessary we indicate this by return the previous stack
        # as our result (i.e. the result of the merge is no change,
        # so the block does not need re-walking.

        if previous is self:
            return previous

        if previous.depth != self.depth:
            raise StackMergeError(ops, (previous, self))

        merged = Stack(self.funcname)
        for slot in range(self.depth):
            selem = self[slot]
            pelem = previous[slot]

            if pelem is selem:
                merged.__push_back(pelem)
                continue

            # Merge the types.
            merged_type = pelem.type.lowest_common_ancestor(selem.type)
            if merged_type is None:
                raise StackMergeError(ops, (previous, self), slot)

            # Merge the values.
            if pelem.value == selem.value:
                merged_value = pelem.value
            else:
                merged_value = None

            # Merge the names.
            merged_names = []
            for name in pelem.names:
                if name in selem.names:
                    merged_names.append(name)

            if (merged_type == pelem.type
                and merged_value == pelem.value
                and merged_names == pelem.names):
                merged_elem = pelem
            else:
                merged_elem = Element(merged_type, None, merged_value)
                merged_elem.names = merged_names

            merged.__push_back(merged_elem)

        if merged.slots == previous.slots:
            return previous

        merged.is_mutable = previous.is_mutable
        merged.max_depth = max(previous.max_depth, self.max_depth)
        return merged

class Element:
    def __init__(self, thetype, name=None, value=None):
        assert thetype is not None
        assert isinstance(thetype, Type)
        self.type = thetype
        self.names = []
        if name is not None:
            assert isinstance(name, names.Name)
            self.names.append(name)
        if value is not None:
            assert isinstance(value, integer)
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
        for node in parameters.children:
            node.accept(self)

    def visit_parameter(self, param):
        type = param.typename.type
        name = param.name.value
        self.entry_stack.push(Element(type, name))

    def visit_externals(self, externals):
        for node in externals.children:
            node.accept(self)

    def visit_external(self, external):
        type = external.typename.type
        name = external.name.value
        if not type.is_function:
            if not type.basetype is PTRTYPE:
                raise ParsedError(
                    external.typename,
                    op, "%s: invalid type for ‘extern’" % type.name)
            if not name.is_shortname:
                raise ParsedError(
                    external.name,
                    "%s: invalid name for ‘extern %s’" % (
                        name, type.name))
        self.entry_stack.push(Element(type, name))

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
        old_entry_stack = getattr(block, "entry_stack", None)
        if old_entry_stack is not None:
            new_entry_stack = new_entry_stack.merge_into(
                old_entry_stack, (from_block.last_op,
                                  block.first_op))
            if new_entry_stack is old_entry_stack:
                return # We've walked this block with this stack
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
        if INTTYPE not in basetypes:
            raise StackTypeError(op, self.stack)
        if PTRTYPE in basetypes:
            rtype = PTRTYPE
        else:
            rtype = fulltypes[0].lowest_common_ancestor(fulltypes[1])
            if rtype is None:
                # One of the types was not INTTYPE
                raise StackTypeError(op, self.stack)
        # Now pop everything and push the result
        self.stack.pop()
        self.stack.pop()
        self.stack.push(Element(rtype))

    def visit_branchop(self, op):
        assert self.stack[0].type is BOOLTYPE
        self.stack.pop()
        self.__leave_block()

    # and, div, mod, mul, or, shl, shr, shra, xor
    def visit_binaryop(self, op):
        # Check the types before mutating the stack
        # so any error messages show the whole setup
        fulltypes = [self.stack[index].type for index in (0, 1)]
        basetypes = [type.basetype for type in fulltypes]
        if basetypes != [INTTYPE, INTTYPE]:
            raise StackTypeError(op, self.stack)
        rtype = fulltypes[0].lowest_common_ancestor(fulltypes[1])
        assert rtype is not None
        self.stack.pop()
        self.stack.pop()
        self.stack.push(Element(rtype))

    def visit_callop(self, op):
        # Check the types before mutating the stack
        # so any error messages show the whole setup
        ftype = self.stack[0].basetype
        if not ftype.is_function:
            raise StackError(op, self.stack, "stack[0] not a function:")
        num_params = len(ftype.paramtypes)
        self.stack.underflow_check(1 + num_params)
        for pindex in range(num_params):
            sindex = num_params - pindex
            ptype = ftype.paramtypes[pindex]
            stype = self.stack[sindex].type
            if stype.basetype != ptype.basetype:
                raise StackError(op, self.stack,
                                 "wrong type in stack[%d]" % sindex)
        # Now pop everything and push the result
        for i in range(1 + num_params):
            self.stack.pop()
        num_returns = len(ftype.returntypes)
        for sindex in range(num_returns):
            rindex = num_returns - sindex - 1
            self.stack.push(Element(ftype.returntypes[rindex]))

    def visit_castop(self, op):
        self.__pick_op = op
        op.slot.accept(self)
        del self.__pick_op
        self.stack.cast_slot(self.__pick_index, op.type)
        del self.__pick_index

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
        self.stack.push(Element(BOOLTYPE))

    def visit_constop(self, op):
        self.stack.push(Element(op.type, value=op.value))

    def visit_derefop(self, op):
        rtype = op.type
        if not rtype.is_computable:
            raise ParsedError(
                op, "%s: invalid type for ‘deref’" % rtype.name)
        # Check the types before mutating the stack
        # so any error messages show the whole setup
        type = self.stack[0].type
        if not type.basetype is PTRTYPE:
            raise StackTypeError(op, self.stack)
        self.stack.pop()
        self.stack.push(Element(rtype))

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
                             "declaration shadows slot %s" % (
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
                             "no slot matches ‘%s’" % name)
        elif len(indexes) != 1:
            raise StackError(self.__pick_op, self.stack,
                             "multiple slots match ‘%s’" % name)
        else:
            self.__pick_index = indexes[0]

    def visit_subop(self, op):
        # Check the types before mutating the stack
        # so any error messages show the whole setup
        fulltypes = [self.stack[index].type for index in (0, 1)]
        basetypes = [type.basetype for type in fulltypes]
        if basetypes == [INTTYPE, PTRTYPE]:
            rtype = PTRTYPE
        elif basetypes == [INTTYPE, INTTYPE]:
            rtype = fulltypes[0].lowest_common_ancestor(fulltypes[1])
            assert rtype is not None
        else:
            raise StackTypeError(op, self.stack)
        self.stack.pop()
        self.stack.pop()
        self.stack.push(Element(rtype))

    def visit_returnop(self, op):
        num_returns = len(self.returntypes)
        for index in range(num_returns):
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
        if self.stack[0].basetype is not INTTYPE:
            raise StackTypeError(op, self.stack)
        a = self.stack.pop()
        self.stack.push(Element(a.type))

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

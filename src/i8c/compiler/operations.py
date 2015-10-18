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

from . import parser
from . import visitors

class Operation(visitors.Visitable):
    """Base class for all operations.
    """
    def __init__(self, ast):
        self.ast = ast

    @property
    def fileline(self):
        return self.ast.fileline

    @property
    def source(self):
        """Source file text this operation was created from.
        """
        return " ".join((token.text for token in self.ast.tokens))

    @property
    def is_block_terminal(self):
        return isinstance(self, TerminalOp)

    @property
    def is_branch(self):
        return isinstance(self, BranchOp)

    @property
    def is_goto(self):
        return isinstance(self, GotoOp)

    @property
    def is_return(self):
        return isinstance(self, ReturnOp)

    @property
    def is_jump(self):
        return self.is_goto or self.is_return

    @property
    def is_comparison(self):
        return isinstance(self, CompareOp)

    @property
    def is_load_constant(self):
        return isinstance(self, ConstOp)

    @property
    def is_add(self):
        return isinstance(self, AddOp)

    @property
    def is_noop(self):
        return isinstance(self, NoOp)

    def __eq__(self, other): # pragma: no cover
        # This comparison is excluded from coverage because it's
        # not currently entered (but it must be defined because
        # we've defined __ne__ below).
        return not (self != other)

    def __ne__(self, other): # pragma: no cover
        # This function is excluded from coverage because it
        # should not be entered.  If it is entered from the
        # testsuite the exception will cause whatever test
        # entered it to fail.
        raise NotImplementedError("%s.__ne__" % self.classname)

    def __hash__(self):
        # This is just the default implementation (I think!)  but
        # it's needed for Python 3 which marks objects unhashable
        # if they define __eq__ without also defining __hash__.
        return hash(id(self))

    def __str__(self):
        return '%s("%s")' % (self.classname, self.source)

# XXX

class NameFromSourceMixin:
    @property
    def dwarfname(self):
        return self.ast.tokens[0].text

# Operations that can be compared just by comparing their class.
# We check two ways to allow regular and synthetic operations to
# be equal.

class ClassComparableOp(Operation):
    def __eq__(self, other):
        return (isinstance(self, other.__class__)
                or isinstance(other, self.__class__))

    def __ne__(self, other): # pragma: no cover
        # This comparison is excluded from coverage because it's
        # not currently entered (but it must be defined because
        # we've defined __eq__ above).
        return not (self == other)

    def __hash__(self):
        # This is just the default implementation (I think!)  but
        # it's needed for Python 3 which marks objects unhashable
        # if they define __eq__ without also defining __hash__.
        return hash(id(self))

# Block-terminating operations.  Note that these are class-comparable,
# meaning exits are not checked, only the operations themselves.  Code
# comparing block-terminating operations must ensure exits are also
# checked if required.

class TerminalOp(ClassComparableOp):
    """Base class for operations that terminate their basic block.
    """

class BranchOp(TerminalOp):
    BRANCHED_EXIT = 0
    NOBRANCH_EXIT = 1

    dwarfname = "bra"

    @property
    def exit_labels(self):
        yield self.ast.target.name
        yield self.fallthrough

class GotoOp(TerminalOp):
    dwarfname = "skip"

    @property
    def exit_labels(self):
        yield self.ast.target.name

class ReturnOp(TerminalOp):
    exit_labels = ()

# Synthetic block-terminating operations

class SyntheticGoto(GotoOp):
    def __init__(self, template, target=None):
        assert isinstance(template, Operation)
        GotoOp.__init__(self, parser.SyntheticNode(template.ast,
                                                   "goto"))
        if target is not None:
            self.target = target

    @property
    def exit_labels(self):
        yield self.target

class SyntheticReturn(ReturnOp):
    def __init__(self, template):
        assert isinstance(template, Operation)
        ReturnOp.__init__(self, parser.SyntheticNode(template.ast,
                                                     "return"))

# XXX

class UnaryOp(ClassComparableOp, NameFromSourceMixin):
    """An operator with no operands that pops one value and pushes one
    back."""
    arity, verb = 1, "operate on"

class BinaryOp(ClassComparableOp, NameFromSourceMixin):
    """An operator with no operands that pops two values and pushes
    one back."""
    arity, verb = 2, "operate on"

# XXX

AbsOp = UnaryOp
AndOp = BinaryOp

class AddOp(BinaryOp):
    dwarfname = "plus"

class PlusUConst(Operation):
    dwarfname = "plus_uconst"

    def __init__(self, template):
        assert template.value != 0
        Operation.__init__(self, template.ast)
        self.value = template.value

class CallOp(ClassComparableOp):
    dwarfname = "call"

class CastOp(Operation):
    @property
    def slot(self):
        return self.ast.slot

    @property
    def type(self):
        return self.ast.typename.type

class CompareOp(Operation):
    arity, verb = 2, "compare"

    REVERSE = {"lt": "ge", "le": "gt", "eq": "ne",
               "ne": "eq", "ge": "lt", "gt": "le"}

    def __init__(self, ast):
        Operation.__init__(self, ast)
        self.reversed = False

    @property
    def dwarfname(self):
        name = self.ast.tokens[0].text[-2:]
        if self.reversed:
            name = self.REVERSE[name]
        return name

    def reverse(self):
        self.reversed = not self.reversed

class ConstOp(Operation):
    @property
    def type(self):
        return self.ast.operand.type

    @property
    def value(self):
        return self.ast.operand.value

class DerefOp(Operation):
    arity, verb = 1, "dereference to"

    @property
    def type(self):
        return self.ast.operand.type

DivOp = BinaryOp

class DropOp(ClassComparableOp, NameFromSourceMixin):
    pass

class DupOp(ClassComparableOp, NameFromSourceMixin):
    pass

ModOp = BinaryOp
MulOp = BinaryOp

class NameOp(Operation):
    @property
    def name(self):
        return self.ast.name.value

    @property
    def slot(self):
        return self.ast.slot.value

NegOp = UnaryOp

class NoOp(Operation):
    pass

NotOp = UnaryOp
OrOp = BinaryOp

class OverOp(ClassComparableOp, NameFromSourceMixin):
    pass

class PickOp(Operation):
    @property
    def operand(self):
        return self.ast.operand

ShlOp = BinaryOp
ShrOp = BinaryOp # Welcome to Shropshire
ShraOp = BinaryOp

class SubOp(BinaryOp):
    dwarfname = "minus"

class SwapOp(ClassComparableOp, NameFromSourceMixin):
    pass

class RotOp(ClassComparableOp, NameFromSourceMixin):
    pass

XorOp = BinaryOp

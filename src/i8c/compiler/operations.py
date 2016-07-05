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

from ..compat import integer
from . import parser
from . import visitors
from .types import PTRTYPE

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
    def is_branch(self):
        return isinstance(self, BranchOp)

    @property
    def is_goto(self):
        return isinstance(self, GotoOp)

    @property
    def is_return(self):
        return isinstance(self, ReturnOp)

    @property
    def is_comparison(self):
        return isinstance(self, CompareOp)

    @property
    def is_load_constant(self):
        return isinstance(self, ConstOp)

    @property
    def is_add(self):
        return isinstance(self, AddOp)

    def __str__(self):
        return '%s("%s")' % (self.__class__.__name__, self.source)

    def is_equivalent_to(self, other):
        if self.is_return and other.is_return:
            return True
        if self.dwarfname != other.dwarfname:
            return False
        assert self.operands == other.operands
        for operand in self.operands:
            if getattr(self, operand) != getattr(other, operand):
                return False
        return True

# All operations either terminate or don't terminate basic blocks.

class TerminalOp(Operation):
    """Base class for all operations that terminate their basic block.
    """
    is_block_terminal = True

class NonTerminalOp(Operation):
    """Base class for all operations that don't terminate basic blocks.
    """
    is_block_terminal = False

    @property
    def dwarfname(self):
        return self.ast.tokens[0].text

# Block-terminating operations.

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

# Synthetic block-terminating operations.

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
# Non-block-terminating operations.

class NoOperandsOp(NonTerminalOp):
    """Base class for all non-terminal operations without operands.
    """
    operands = ()

# Generic non-block-terminating operations.

class UnaryOp(NoOperandsOp):
    """A math or logic operator that pops one value and pushes one
    back."""
    arity, verb = 1, "operate on"

class BinaryOp(NoOperandsOp):
    """An math or logic operator that pops two values and pushes one
    back."""
    arity, verb = 2, "operate on"

class CompareOp(NoOperandsOp):
    """A comparison operator which pops two values and pushes one
    back."""
    arity, verb = 2, "compare"

    REVERSE = {"lt": "ge", "le": "gt", "eq": "ne",
               "ne": "eq", "ge": "lt", "gt": "le"}

    def __init__(self, ast):
        NonTerminalOp.__init__(self, ast)
        self.reversed = False

    @property
    def dwarfname(self):
        name = self.ast.tokens[0].text[-2:]
        if self.reversed:
            name = self.REVERSE[name]
        return name

    def reverse(self):
        self.reversed = not self.reversed

# Specific non-block-terminating operations.

AbsOp = UnaryOp
AndOp = BinaryOp

class AddOp(BinaryOp):
    dwarfname = "plus"

class PlusUConst(NonTerminalOp):
    dwarfname = "plus_uconst"
    operands = ("value",)

    def __init__(self, template):
        assert template.value != 0
        NonTerminalOp.__init__(self, template.ast)
        self.value = template.value

class CallOp(NoOperandsOp):
    dwarfname = "call"

class CastOp(NonTerminalOp):
    operands = ("slot", "old_type", "new_type")

    @property
    def slot(self):
        return self.ast.slot.value

    @property
    def new_type(self):
        return self.ast.typename.type

class ConstOp(NonTerminalOp):
    operands = ("type", "value")

    @property
    def type(self):
        return self.ast.operand.type

    @property
    def value(self):
        return self.ast.operand.value

class DerefOp(NonTerminalOp):
    arity, verb = 1, "dereference to"
    operands = ("type",)

    @property
    def type(self):
        return self.ast.operand.type

DivOp = BinaryOp

class DropOp(NoOperandsOp):
    pass

class LoadOp(NonTerminalOp):
    def __init__(self, ast):
        NonTerminalOp.__init__(self, ast)
        self.__operand = None

    @property
    def is_resolved(self):
        return self.__operand is not None

    # XXX

    @property
    def is_pick(self):
        assert self.is_resolved
        return isinstance(self.__operand, integer)

    @property
    def is_loadext(self):
        return not self.is_pick

    # Accessors for "pickslot" and "external"

    @property
    def pickslot(self):
        assert self.is_pick
        return self.__operand

    @pickslot.setter
    def pickslot(self, value):
        assert not self.is_resolved
        self.__operand = value
        assert self.is_pick

    @property
    def external(self):
        assert self.is_loadext
        return self.__operand

    @external.setter
    def external(self, value):
        assert not self.is_resolved
        self.__operand = value
        assert self.is_loadext

    # XXX

    @property
    def operands(self):
        if self.is_pick:
            operand = "pickslot"
        else:
            assert self.is_loadext
            operand = "external"
        return (operand,)

    @property
    def dwarfname(self):
        if self.is_pick:
            return {0: "dup", 1: "over"}.get(self.pickslot, "pick")
        assert self.is_loadext
        if self.external.basetype is PTRTYPE:
            return "addr"
        assert self.external.type.is_function
        return "load_external"

    # The thing we are trying to load

    @property
    def name(self):
        return self.ast.name.value

ModOp = BinaryOp
MulOp = BinaryOp

class NameOp(NonTerminalOp):
    operands = ("slot", "newname")

    @property
    def slot(self):
        return self.ast.slot.value

    @property
    def newname(self):
        return self.ast.newname.value

NegOp = UnaryOp
NotOp = UnaryOp
OrOp = BinaryOp

class PickOp(LoadOp):
    def __init__(self, ast, slot):
        LoadOp.__init__(self, ast)
        self.pickslot = slot

ShlOp = BinaryOp
ShrOp = BinaryOp # Welcome to Shropshire
ShraOp = BinaryOp

class SubOp(BinaryOp):
    dwarfname = "minus"

class SwapOp(NoOperandsOp):
    pass

class RotOp(NoOperandsOp):
    pass

class WarnOp(NonTerminalOp):
    dwarfname = "warn"
    operands = ("message",)

    @property
    def value(self):
        return self.ast.operand.value

XorOp = BinaryOp

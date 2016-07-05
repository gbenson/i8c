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
from . import RedefinedIdentError
from . import UndefinedIdentError
from . import visitors
from . import warn
from .operations import *

debug_print = logger.debug_printer_for(__name__)

class BlockLabel(NonTerminalOp):
    """Placeholder used only during block creation."""

    @property
    def name(self):
        return self.ast.name

class BasicBlock(visitors.Visitable):
    def __init__(self, index):
        self.index = index
        self.label = None
        self.entries = {}
        self.ops = []

    @property
    def fileline(self):
        return self.ops[0].fileline

    @property
    def name(self):
        return "Block #%d (%s)" % (self.index,
                                   (self.label is not None
                                    and '"%s"' % self.label
                                    or self.fileline))

    @property
    def first_op(self):
        return self.ops[0]

    @property
    def last_op(self):
        return self.ops[-1]

    @property
    def is_terminated(self):
        return self.ops and self.last_op.is_block_terminal

    @property
    def is_branch_terminated(self):
        return self.ops and self.last_op.is_branch

    @property
    def branched_exit(self):
        assert self.is_branch_terminated
        assert len(self.exits) == 2
        return self.exits[BranchOp.BRANCHED_EXIT]

    @property
    def nobranch_exit(self):
        assert self.is_branch_terminated
        assert len(self.exits) == 2
        return self.exits[BranchOp.NOBRANCH_EXIT]

    @property
    def is_goto_terminated(self):
        return self.ops and self.last_op.is_goto

    @property
    def goto_exit(self):
        assert self.is_goto_terminated
        assert len(self.exits) == 1
        return self.exits[0]

    @property
    def is_return_terminated(self):
        return self.ops and self.last_op.is_return

    def append(self, op):
        assert not self.is_terminated
        if isinstance(op, BlockLabel):
            assert self.label is None
            self.label = op.name
        self.ops.append(op)

    def set_exits(self, labels):
        try:
            self.exits = [labels[label]
                          for label in self.last_op.exit_labels]
        except KeyError as e:
            raise UndefinedIdentError(self.last_op, "label", e.args[0])

    def __str__(self):
        result = self.name
        if hasattr(self, "exits"):
            result += ", "
            if len(self.exits) == 0:
                result += "no exits"
            elif len(self.exits) == 1:
                result += "next block = #%d" % self.exits[0].index
            else:
                result += "exits = %s" % ", ".join(
                    ("#%d" % block.index for block in self.exits))
        result += ":"
        entry_stack = getattr(self, "entry_stack", None)
        if entry_stack is not None:
            result += "\n%s\n  ---" % entry_stack
        for op in self.ops:
            result += "\n  %s" % op
        return result

    def is_equivalent_to(self, other):
        assert not self is other

        # Quickly reject mismatches
        if other.exits != self.exits:
            return False
        if len(other.ops) != len(self.ops):
            return False
        if other.entry_stack.depth != self.entry_stack.depth:
            return False

        # Check the operations
        for op1, op2 in zip(other.ops, self.ops):
            if not op1.is_equivalent_to(op2):
                return False

        # Check the entry stacks
        for index in range(self.entry_stack.depth):
            bt1 = other.entry_stack[index].basetype
            bt2 = self.entry_stack[index].basetype
            if bt1 != bt2:
                return False

        return True

    def replace_exit(self, old, new):
        self.exits = [block == old and new or block
                      for block in self.exits]

class Label(object):
    is_builtin = False

    def __init__(self, ast, pc):
        self.ast = ast
        self.pc = pc

    @property
    def fileline(self):
        return self.ast.fileline

class SyntheticLabel(Label):
    def __init__(self, pc):
        Label.__init__(self, None, pc)

class BlockCreator(object):
    def visit_toplevel(self, toplevel):
        for node in toplevel.functions:
            node.accept(self)

    def visit_function(self, function):
        self.blocks = {}
        self.labels = {}
        self.__block = None
        self.pc = 0

        function.ops.accept(self)
        del function.ops
        self.ensure_has_blocks(function)
        self.ensure_all_blocks_terminated()

        labels = {}
        for name, label in self.labels.items():
            labels[name] = self.blocks[label.pc]
        del self.labels

        blocks = sorted(self.blocks.items())
        blocks = [block for start_pc, block in blocks]
        del self.blocks

        for block in blocks:
            block.set_exits(labels)
            for exit_block in block.exits:
                exit_block.entries[block] = True
        for block in blocks:
            block.entries = list(block.entries.keys())

        if debug_print.is_enabled:
            for block in blocks:
                debug_print(str(block) + "\n\n")

        function.entry_block = blocks[0]
        function.entry_block.entries.append(None)

        for block in blocks:
            if not block.entries:
                warn("code is unreachable", block)

    def new_synthetic_label(self, target):
        # Create a synthetic label.  Using an integer
        # means it cannot clash with any user-supplied
        # labels as they are all strings.
        label = len(self.labels)
        assert label not in self.labels
        self.labels[label] = SyntheticLabel(target)
        return label

    def ensure_has_blocks(self, function):
        if self.blocks:
            return
        self.add_op(SyntheticReturn(Operation(function)))

    def ensure_all_blocks_terminated(self):
        blocks = sorted(self.blocks.items())
        start_pcs = [start_pc for start_pc, block in blocks]
        blocks = [block for start_pc, block in blocks]
        for block, next_pc in zip(blocks, start_pcs[1:] + [None]):
            op = block.last_op
            if not block.is_terminated:
                if next_pc is None:
                    block.append(SyntheticReturn(op))
                else:
                    label = self.new_synthetic_label(next_pc)
                    block.append(SyntheticGoto(op, label))
            elif block.is_branch_terminated:
                if next_pc is None:
                    label = self.new_synthetic_label(self.pc)
                    self.add_op(SyntheticReturn(op))
                else:
                    label = self.new_synthetic_label(next_pc)
                op.fallthrough = label
            if isinstance(block.first_op, BlockLabel):
                block.ops.pop(0)

    @property
    def current_block(self):
        if self.__block is None:
            assert self.pc not in self.blocks
            self.__block = BasicBlock(len(self.blocks))
            self.blocks[self.pc] = self.__block
        return self.__block

    def drop_current_block(self):
        self.__block = None

    def add_op(self, op):
        block = self.current_block
        block.append(op)
        if block.is_terminated:
            self.drop_current_block()
        self.pc += 1

    def visit_operations(self, ops):
        for child in ops.children:
            child.accept(self)

    def visit_label(self, label):
        prev = self.labels.get(label.name, None)
        if prev is not None:
            raise RedefinedIdentError(label, "label", label.name, prev)
        self.labels[label.name] = Label(label, self.pc)
        self.drop_current_block()
        self.add_op(BlockLabel(label))

    # Operations

    def visit_simpleop(self, op):
        self.add_op(globals()[op.name.title() + "Op"](op))

    def visit_castop(self, op):
        self.add_op(CastOp(op))

    def visit_compareop(self, op):
        self.add_op(CompareOp(op))

    def visit_condbranchop(self, op):
        self.add_op(CompareOp(op))
        self.add_op(BranchOp(op))

    def visit_derefop(self, op):
        self.add_op(DerefOp(op))

    def visit_dupop(self, op):
        self.add_op(PickOp(op, 0))

    def visit_gotoop(self, op):
        self.add_op(GotoOp(op))

    def visit_loadop(self, op):
        if hasattr(op.operand, "type"):
            self.add_op(ConstOp(op))
        else:
            self.add_op(LoadOp(op))

    def visit_nameop(self, op):
        self.add_op(NameOp(op))

    def visit_overop(self, op):
        self.add_op(PickOp(op, 1))

    def visit_pickop(self, op):
        self.add_op(PickOp(op, op.operand.value))

    def visit_returnop(self, op):
        self.add_op(ReturnOp(op))

    def visit_warnop(self, op):
        self.add_op(WarnOp(op))

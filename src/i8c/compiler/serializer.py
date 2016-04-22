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

from . import blocks
from . import logger
from . import operations
from . import visitors

debug_print = logger.debug_printer_for(__name__)

class StopBlock(blocks.BasicBlock):
    def __init__(self, ast):
        blocks.BasicBlock.__init__(self, None)
        self.append(StopOp(ast))

class StopOp(operations.Operation):
    @property
    def source(self):
        return "EOF"

class OperationStream(visitors.Visitable):
    def __init__(self, function):
        self.ops = {}
        self.jumps = {}
        self.labels = {}
        self.__eof_block = StopBlock(function)

    @property
    def is_closed(self):
        return self.__eof_block is None

    @property
    def items(self):
        assert self.is_closed
        return self.ops.items

    @property
    def stream(self):
        return sorted(self.items())

    # Methods used to build the stream

    @property
    def last_op(self):
        assert not self.is_closed
        assert self.ops
        return self.ops[len(self.ops) - 1]

    def append(self, op):
        assert not self.is_closed
        self.ops[len(self.ops)] = op

    def jump_from_last_to(self, target):
        assert not self.is_closed
        source, target = self.last_op, target.first_op

        if target not in self.labels:
            self.labels[target] = []
        self.labels[target].append(source)

        assert source not in self.jumps
        self.jumps[source] = target

    def jump_from_last_to_EOF(self):
        self.jump_from_last_to(self.__eof_block)

    def close(self):
        assert not self.is_closed
        self.append(self.__eof_block.first_op)
        self.__eof_block = None
        self.__replace_returns_with_gotos()

    def __replace_returns_with_gotos(self):
        for index, op in self.ops.items():
            if not op.is_return:
                continue
            self.replace_by_index(index, operations.SyntheticGoto(op))

    # Methods used to mutate the stream

    def replace_by_index(self, index, new_op):
        self.replace_by_index_op(index, self.ops[index], new_op)

    def replace_by_index_op(self, index, old_op, new_op):
        assert self.is_closed

        for dict in self.labels, self.jumps:
            assert new_op not in dict
            tmp = dict.pop(old_op, None)
            if tmp is not None:
                dict[new_op] = tmp

        for lbl_ops in self.labels.values():
            for lbl_op, lbl_index in zip(lbl_ops, range(len(lbl_ops))):
                if lbl_op is old_op:
                    lbl_ops[lbl_index] = new_op

        for jump_src, jump_tgt in self.jumps.items():
            if jump_tgt is old_op:
                self.jumps[jump_src] = new_op

        self.ops[index] = new_op

    def remove_by_index_op(self, index, op):
        assert self.is_closed
        assert op not in self.labels

        target = self.jumps.pop(op, None)
        if target is not None:
            self.__remove_label(target, op)

        check = self.ops.pop(index)
        assert op == check
        self.__reindex()

    def retarget_jump(self, from_op, to_op):
        assert self.is_closed

        trampoline = self.jumps[from_op]
        self.__remove_label(trampoline, from_op)
        self.jumps[from_op] = to_op
        self.labels[to_op].append(from_op)

    def __remove_label(self, target, source):
        assert self.is_closed
        self.labels[target].remove(source)
        if not self.labels[target]:
            del self.labels[target]

    def __reindex(self):
        ops = self.stream
        self.ops = {}
        for index, op in ops:
            self.ops[len(self.ops)] = op

    # Debug printing

    def __str__(self):
        reverse = {}
        for index, op in self.ops.items():
            reverse[op] = index
        lines = []
        for index, op in self.ops.items():
            line = []
            sources = self.labels.get(op, None)
            if sources is not None:
                line.append("%d:" % index)
            line.append("\t%s" % op)
            jump = self.jumps.get(op, None)
            if jump is not None:
                line.append(" -> %d" % reverse[jump])
            lines.append("".join(line))
        return "\n".join(lines)

class Serializer(object):
    def visit_toplevel(self, toplevel):
        for node in toplevel.functions:
            node.accept(self)

    def visit_function(self, function):
        self.stream = OperationStream(function)
        self.visited = {}
        function.entry_block.accept(self)
        del function.entry_block
        self.stream.close()
        debug_print("%s:\n" % function.name.value)
        debug_print("%s\n\n" % self.stream)
        function.ops = self.stream

    def visit_basicblock(self, block):
        if self.visited.get(block, False):
            return
        self.visited[block] = True

        for op in block.ops:
            self.stream.append(op)

        if block.is_branch_terminated:
            self.stream.jump_from_last_to(block.branched_exit)

            self.stream.append(operations.SyntheticGoto(self.stream.last_op))
            self.stream.jump_from_last_to(block.nobranch_exit)

            block.nobranch_exit.accept(self)
            block.branched_exit.accept(self)
        elif block.is_goto_terminated:
            self.stream.jump_from_last_to(block.goto_exit)

            block.goto_exit.accept(self)
        else:
            assert block.is_return_terminated
            assert not block.exits

            self.stream.jump_from_last_to_EOF()

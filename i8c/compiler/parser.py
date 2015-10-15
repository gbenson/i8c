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

from ..compat import next
from . import lexer
from . import logger
from . import ParserError
from . import ParsedError
from . import visitors
import copy
from operator import eq as EXACTLY, ge as ATLEAST

debug_print = logger.debug_printer_for(__name__)

def raise_unless_len(tokens, cmp, count):
    if cmp(len(tokens), count):
        return
    # Try to narrow down to an offending token
    if cmp == EXACTLY and len(tokens) > count:
        index = count
    else:
        index = -1
    raise ParserError(tokens[index:])

class TreeNode(visitors.Visitable):
    def __init__(self):
        self.tokens = []
        self.children = []

    @property
    def fileline(self):
        return self.tokens[0].fileline

    def add_child(self, klass):
        child = klass()
        self.children.append(child)
        return child

    @property
    def latest_child(self):
        return self.children[-1]

    def some_children(self, classinfo):
        return (child
                for child in self.children
                if isinstance(child, classinfo))

    def one_child(self, classinfo):
        result = None
        for child in self.some_children(classinfo):
            if result is not None:
                self.__one_child_error("multiple", classinfo)
            result = child
        if result is None:
            self.__one_child_error("no", classinfo)
        return result

    def __one_child_error(self, what, classinfo):
        msg = "%s has %s %s" % (
            self.classname,
            what,
            classinfo.__name__)
        raise ParsedError(self, msg.lower())

    def __str__(self):
        lines = []
        self.__dump(lines, "")
        return "\n".join(lines)

    def __dump(self, lines, prefix):
        line = prefix + self.classname
        if isinstance(self, LeafNode):
            line += ': '
            line += " ".join((token.text for token in self.tokens))
        if hasattr(self, "type"):
            # Dump what the type annotator added
            line += " [%s" % self.type.name
            basetype = self.type.basetype
            if basetype is not self.type:
                line += " = %s" % basetype.name
            line += "]"
        lines.append(line)
        for child in self.children:
            child.__dump(lines, prefix + "  ")

class LeafNode(TreeNode):
    def consume(self, tokens):
        if self.tokens:
            raise ParserError(tokens)
        self.tokens = tokens

class SyntheticNode(LeafNode):
    """A node that the block creator created.
    """
    def __init__(self, template, text):
        assert isinstance(template, TreeNode)
        self.tokens = [lexer.SyntheticToken(template.tokens[0],
                                            "synthetic " + text)]

class Identifier(LeafNode):
    def consume(self, tokens):
        raise_unless_len(tokens, EXACTLY, 1)
        if not isinstance(tokens[0], lexer.WORD):
            raise ParserError(tokens)
        LeafNode.consume(self, tokens)

    @property
    def name(self):
        return self.tokens[0].text

class Constant(LeafNode):
    def consume(self, tokens):
        raise_unless_len(tokens, EXACTLY, 1)
        LeafNode.consume(self, tokens)

class Integer(Constant):
    def consume(self, tokens):
        Constant.consume(self, tokens)
        if not isinstance(self.tokens[0], lexer.NUMBER):
            raise ParserError(tokens)
        self.value = self.tokens[0].value

class BuiltinConstant(Constant):
    def consume(self, tokens):
        Constant.consume(self, tokens)
        self.value = self.VALUES.get(tokens[0].text, None)
        if self.value is None:
            raise ParserError(tokens)

class Pointer(BuiltinConstant):
    VALUES = {"NULL": 0}

class Boolean(BuiltinConstant):
    VALUES = {"TRUE": 1, "FALSE": 0}

class TopLevel(TreeNode):
    def consume(self, tokens):
        klass = self.CLASSES.get(tokens[0].text, None)
        if klass is not None:
            self.add_child(klass)
        elif not self.children:
            raise ParserError(tokens)
        self.latest_child.consume(tokens)

    @property
    def typedefs(self):
        return self.some_children(Typedef)

    @property
    def functions(self):
        return self.some_children(Function)

class Typedef(TreeNode):
    def consume(self, tokens):
        raise_unless_len(tokens, ATLEAST, 3)
        if self.tokens:
            raise ParserError(tokens)
        self.tokens = tokens
        self.add_child(TypeName).consume([tokens[-1]])
        tokens = tokens[1:-1]
        self.add_child(Type.class_for(tokens)).pop_consume(tokens)

class TypeName(Identifier):
    pass

class Type:
    @staticmethod
    def class_for(tokens):
        if tokens[0].text == "func":
            return FuncType
        else:
            return BasicType

class BasicType(Identifier, Type):
    def pop_consume(self, tokens):
        if self.tokens:
            raise ParserError(tokens)
        self.tokens = [tokens.pop(0)]

class FuncType(TreeNode, Type):
    def pop_consume(self, tokens):
        if self.tokens:
            raise ParserError(tokens)
        self.tokens = [tokens.pop(0)]
        self.add_child(ReturnTypes).pop_consume(tokens, lexer.OPAREN)
        assert tokens and isinstance(tokens[0], lexer.OPAREN)
        tokens.pop(0)
        self.add_child(ParamTypes).pop_consume(tokens, lexer.CPAREN)
        assert tokens and isinstance(tokens[0], lexer.CPAREN)
        tokens.pop(0)

    @property
    def returntypes(self):
        return self.one_child(ReturnTypes)

    @property
    def paramtypes(self):
        return self.one_child(ParamTypes)

class TypeList(TreeNode):
    def pop_consume(self, tokens, stop_at=None):
        self.tokens = copy.copy(tokens)
        while tokens:
            if stop_at is not None and isinstance(tokens[0], stop_at):
                break
            self.add_child(Type.class_for(tokens)).pop_consume(tokens)
            if tokens:
                if stop_at is not None and isinstance(tokens[0], stop_at):
                    break
                if not isinstance(tokens[0], lexer.COMMA):
                    raise ParserError(tokens)
                tokens.pop(0)
        else:
            if stop_at is not None:
                raise ParserError(tokens)

class ReturnTypes(TypeList):
    pass

class ParamTypes(TypeList):
    pass

class Function(TreeNode):
    def consume(self, tokens):
        if not self.tokens:
            raise_unless_len(tokens, ATLEAST, 4)
            self.tokens = tokens
            self.add_child(FullName).consume(tokens[1:4])
            tokens = tokens[4:]
            if tokens:
                if tokens[0].text != "returns":
                    raise ParserError(tokens)
                tokens.pop(0)
            self.returntypes = self.add_child(ReturnTypes)
            self.returntypes.pop_consume(tokens)
            self.parameters = self.add_child(Parameters)
            self.externals = self.add_child(Externals)
            self.operations = self.add_child(Operations)
            return

        if tokens[0].text == "argument":
            if self.externals.children or self.operations.children:
                raise ParserError(tokens)
            self.parameters.consume(tokens)
        elif tokens[0].text == "extern":
            if self.operations.children:
                raise ParserError(tokens)
            self.externals.consume(tokens)
        else:
            self.operations.consume(tokens)

    @property
    def name(self):
        return self.one_child(FullName)

    @property
    def entry_stack(self):
        return self.some_children((Parameters, Externals))

TopLevel.CLASSES = {"define": Function, "typedef": Typedef}

class FullName(TreeNode):
    def consume(self, tokens):
        raise_unless_len(tokens, EXACTLY, 3)
        if (self.tokens
            or not isinstance(tokens[1], lexer.DOUBLE_COLON)):
            raise ParserError(tokens)
        self.tokens = tokens
        self.add_child(Provider).consume([tokens[0]])
        self.add_child(ShortName).consume([tokens[2]])

    @property
    def provider(self):
        return self.one_child(Provider).name

    @property
    def shortname(self):
        return self.one_child(ShortName).name

    @property
    def ident(self):
        """How will the user refer to this item in the source?"""
        return "%s::%s" % (self.one_child(Provider).name,
                           self.one_child(ShortName).name)

class Provider(Identifier):
    pass

class ShortName(Identifier):
    pass

class TypeAndName(TreeNode):
    def consume(self, tokens, allow_fullname):
        self.add_child(Type.class_for(tokens)).pop_consume(tokens)
        if allow_fullname and len(tokens) == 3:
            klass = FullName
        elif len(tokens) == 1:
            klass = ShortName
        else:
            raise ParserError(self.tokens)
        self.add_child(klass).consume(tokens)

    @property
    def typename(self):
        return self.one_child(Type)

    @property
    def name(self):
        return self.one_child((ShortName, FullName))

class Parameters(TreeNode):
    def consume(self, tokens):
        if not self.tokens:
            self.tokens = tokens
        self.add_child(Parameter).consume(tokens)

class Parameter(TypeAndName):
    def consume(self, tokens):
        if self.tokens:
            raise ParserError(tokens)
        raise_unless_len(tokens, ATLEAST, 3)
        self.tokens = tokens
        TypeAndName.consume(self, tokens[1:], False)

class Externals(TreeNode):
    def consume(self, tokens):
        if not self.tokens:
            self.tokens = tokens
        self.add_child(External).consume(tokens)

class External(TypeAndName):
    def consume(self, tokens):
        if self.tokens:
            raise ParserError(tokens)
        raise_unless_len(tokens, ATLEAST, 3)
        self.tokens = tokens
        TypeAndName.consume(self, tokens[1:], True)

# XXX

class Label(Identifier):
    def consume(self, tokens):
        Identifier.consume(self, [tokens[0]])

# Base mixin for all operations

class Operation:
    def consume(self, tokens):
        if self.tokens:
            raise ParserError(tokens)
        raise_unless_len(tokens, EXACTLY, 1 + self.num_args)
        self.tokens = tokens
        if self.num_args > 0:
            self.add_children(*tokens[1:])

    @property
    def operand(self):
        assert len(self.children) == 1
        return self.children[0]

# XXX blah blah blah

class TreeOp(TreeNode, Operation):
    pass

class NoArgOp(LeafNode, Operation):
    num_args = 0

class OneArgOp(TreeOp):
    num_args = 1

class TwoArgOp(TreeOp):
    num_args = 2

class JumpOp(OneArgOp):
    def add_children(self, target):
        self.add_child(Target).consume([target])

    @property
    def target(self):
        return self.one_child(Target)

class Target(Identifier):
    pass

class StackSlot(Integer):
    pass

# Classes which represent groups of operators in the parse tree

class SimpleOp(NoArgOp):
    @property
    def name(self):
        return self.tokens[0].text

class CompareOp(NoArgOp):
    pass

class CondBranchOp(JumpOp):
    pass

# Classes for operators that require specific individual parsing

class CastOp(TwoArgOp):
    def add_children(self, slot, type):
        if isinstance(slot, lexer.NUMBER):
            self.add_child(StackSlot).consume([slot])
        else:
            self.add_child(ShortName).consume([slot])
        self.add_child(BasicType).pop_consume([type])

    @property
    def slot(self):
        return self.one_child((StackSlot, ShortName))

    @property
    def typename(self):
        return self.one_child(BasicType)

    @property
    def named_operands(self):
        """Operands that need processing by the name annotator.
        """
        return self.some_children(ShortName)

class DerefOp(OneArgOp):
    def add_children(self, type):
        self.add_child(BasicType).pop_consume([type])

class GotoOp(JumpOp):
    pass

class LoadOp(TreeOp):
    def consume(self, tokens):
        if self.tokens:
            raise ParserError(tokens)
        self.tokens = tokens
        if len(tokens) == 2:
            if isinstance(tokens[1], lexer.NUMBER):
                klass = Integer
            else:
                for klass in Pointer, Boolean:
                    if tokens[1].text in klass.VALUES:
                        break
                else:
                    klass = ShortName
        elif len(self.tokens) == 4:
            klass = FullName
        else:
            raise ParserError(tokens)
        self.add_child(klass).consume(tokens[1:])

    @property
    def named_operands(self):
        """Operands that need processing by the name annotator.
        """
        return self.some_children((ShortName, FullName))

    @property
    def typed_operands(self):
        """Operands that need processing by the type annotator.
        """
        return self.some_children(Constant)

class NameOp(TwoArgOp):
    def add_children(self, slot, name):
        self.add_child(StackSlot).consume([slot])
        self.add_child(ShortName).consume([name])

    @property
    def slot(self):
        return self.one_child(StackSlot)

    @property
    def name(self):
        return self.one_child(ShortName)

class PickOp(OneArgOp):
    def add_children(self, slot):
        self.add_child(StackSlot).consume([slot])

class ReturnOp(NoArgOp):
    pass

# XXX

class Operations(TreeNode):
    CLASSES = {"cast": CastOp,
               "deref": DerefOp,
               "goto": GotoOp,
               "load": LoadOp,
               "name": NameOp,
               "pick": PickOp,
               "return": ReturnOp}
    for op in ("abs", "add", "and", "div", "drop", "dup",
               "call", "mod", "mul", "neg", "not", "or",
               "over", "rot", "shl", "shr", "shra", "sub",
               "swap", "xor"):
        CLASSES[op] = SimpleOp
    for op in ("lt", "le", "eq", "ne", "ge", "gt"):
        CLASSES[op] = CompareOp
        CLASSES["b" + op] = CondBranchOp
    del op

    # Do not add an "addr" instruction for DW_OP_addr.
    # See XXX UNWRITTEN DOCS.
    assert "addr" not in CLASSES

    # Do not add a "bra" instruction, it gives no clue as to why
    # it would branch and makes code harder to read.  Users should
    # use "load NULL, bne" or "load 0, bne" and let the optimizer
    # figure it out.
    assert "bra" not in CLASSES

    # Do not add "plus" or "minus" operations.  To calculate the
    # sum of two values you add them.  To calculate the difference
    # of two values you sub(tract) them.  That is all.
    assert "plus" not in CLASSES
    assert "minus" not in CLASSES

    def consume(self, tokens):
        if not self.tokens:
            self.tokens = tokens
        if len(tokens) == 2 and isinstance(tokens[1], lexer.COLON):
            klass = Label
        else:
            klass = self.CLASSES.get(tokens[0].text, None)
            if klass is None:
                raise ParserError(tokens)
        self.add_child(klass).consume(tokens)

    @property
    def named_operations(self):
        """Operations that need processing by the name annotator.
        """
        return self.some_children((CastOp, LoadOp, NameOp))

    @property
    def typed_operations(self):
        """Operations that need processing by the type annotator.
        """
        return self.some_children((CastOp, DerefOp, LoadOp))

def build_tree(tokens):
    tree = TopLevel()
    try:
        group = None
        terminators = []
        while True:
            if group is None:
                group = []
                terminators.append(lexer.NEWLINE)
            try:
                token = next(tokens)
            except StopIteration:
                break
            if isinstance(token, terminators[-1]):
                terminators.pop()
                if not terminators:
                    tree.consume(group)
                    group = None
                    continue
            elif isinstance(token, lexer.OPAREN):
                terminators.append(lexer.CPAREN)
            if not isinstance(token, lexer.NEWLINE):
                group.append(token)
        if group:
            if terminators == [lexer.NEWLINE]:
                # No newline at end of input
                tree.consume(group)
            else:
                # Unclosed parenthesis?
                raise NotImplementedError
        return tree
    finally:
        if debug_print.is_enabled:
            debug_print("%s\n\n" % tree)

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
            self.__class__.__name__,
            what,
            classinfo.__name__)
        raise ParsedError(self, msg.lower())

    def __str__(self):
        lines = []
        self.__dump(lines, "")
        return "\n".join(lines)

    def __dump(self, lines, prefix):
        line = prefix + self.__class__.__name__
        if isinstance(self, LeafNode):
            line += ': '
            line += " ".join((token.text for token in self.tokens))
        elif isinstance(self, Operation) and not self.has_own_handler:
            line += '("%s")' % self.tokens[0].text
        if hasattr(self, "type"):
            # Dump what the type annotator added
            line += " [%s" % self.type.name
            basetype = self.type.basetype
            if basetype is not self.type:
                line += " = %s" % basetype.name
            line += "]"
        if (isinstance(self, (FullName, ShortName))
            and hasattr(self, "value")):
            # Dump what the name annotator added
            line += " [%s]" % self.value
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

class String(Constant):
    def consume(self, tokens):
        Constant.consume(self, tokens)
        if not isinstance(self.tokens[0], lexer.STRING):
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
        if klass is Wordsize and self.children:
            raise ParserError(tokens)
        if klass is not None:
            if (klass is not External
                  or not self.children
                  or not isinstance(self.latest_child, Function)):
                self.add_child(klass)
        elif not self.children:
            raise ParserError(tokens)
        self.latest_child.consume(tokens)

    @property
    def wordsize_directives(self):
        return self.some_children(Wordsize)

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
            if tokens and isinstance(tokens[0], lexer.WORD):
                # This is a named type.  We've no use for the name
                # right now, but we could replace self.children[-1]
                # with a TypeAndName if we need it for something.
                tokens.pop(0)
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
            self.ops = self.add_child(Operations)
            return

        if tokens[0].text == "argument":
            if self.ops.children:
                raise ParserError(tokens)
            self.parameters.consume(tokens)
        elif tokens[0].text == "extern":
            if self.ops.children:
                raise ParserError(tokens)
            self.externals.consume(tokens)
        else:
            self.ops.consume(tokens)

    @property
    def name(self):
        return self.one_child(FullName)

    @property
    def provider(self):
        return self.name.provider

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
    def consume(self, tokens):
        self.add_child(Type.class_for(tokens)).pop_consume(tokens)
        if self.allow_fullname and len(tokens) == 3:
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
    allow_fullname = False

    def consume(self, tokens):
        if self.tokens:
            raise ParserError(tokens)
        self.tokens = tokens
        TypeAndName.consume(self, tokens[1:])

class Externals(TreeNode):
    def consume(self, tokens):
        if not self.tokens:
            self.tokens = tokens
        self.add_child(External).consume(tokens)

class External(TypeAndName):
    allow_fullname = True

    def consume(self, tokens):
        if self.tokens:
            raise ParserError(tokens)
        self.tokens = tokens
        TypeAndName.consume(self, tokens[1:])

class Wordsize(TreeNode):
    def consume(self, tokens):
        raise_unless_len(tokens, EXACTLY, 2)
        if self.tokens:
            raise ParserError(tokens)
        self.add_child(Integer).consume(tokens[1:])

TopLevel.CLASSES = {
    "define": Function,
    "extern": External,
    "typedef": Typedef,
    "wordsize": Wordsize}

# XXX

class Label(Identifier):
    def consume(self, tokens):
        Identifier.consume(self, [tokens[0]])

# Base class for all operations

class Operation(TreeNode):
    has_own_handler = False
    may_fold_load = False

    def consume(self, tokens):
        if self.tokens:
            raise ParserError(tokens)
        self.tokens = tokens

        # Split the argument list
        tokens, args = tokens[1:], []
        while tokens:
            if isinstance(tokens[0], lexer.COMMA):
                # Comma immediately after operator,
                # or comma immediately after comma
                raise ParserError(tokens)
            arg = []
            while tokens:
                token = tokens.pop(0)
                if not isinstance(token, lexer.COMMA):
                    arg.append(token)
                elif not tokens:
                    # Comma at end of line
                    raise ParserError(token)
                else:
                    break
            assert arg
            args.append(arg)

        # Handle any folded loads
        if self.may_fold_load and len(args) == self.num_args + 1:
            self.add_folded_load(args.pop(0))

        # Process the arguments
        if len(args) > self.num_args:
            raise ParserError(args[self.num_args])
        elif len(args) < self.num_args:
            raise ParserError(self.tokens[-1:])
        else:
            self.add_children(*args)

    def add_folded_load(self, tokens):
        token = lexer.SyntheticToken(tokens[0], "synthetic load")
        self.add_child(LoadOp).consume([token] + tokens)

    @property
    def folded_children(self):
        return self.some_children(Operation)

    @property
    def operand(self):
        non_folded = [child
                      for child in self.children
                      if not isinstance(child, Operation)]
        assert len(non_folded) == 1
        return non_folded[0]

# XXX blah blah blah

class NoArgOp(Operation):
    num_args = 0

    def add_children(self):
        pass

class OneArgOp(Operation):
    num_args = 1

class TwoArgOp(Operation):
    num_args = 2

class JumpOp(OneArgOp):
    def add_children(self, target):
        self.add_child(Target).consume(target)

    @property
    def target(self):
        return self.one_child(Target)

class NameCastOp(TwoArgOp):
    has_own_handler = True

    def add_children(self, slot, arg2):
        if isinstance(slot[0], lexer.NUMBER):
            slotclass = StackSlot
        else:
            slotclass = ShortName
        self.slot = self.add_child(slotclass)
        self.slot.consume(slot)
        self.add_child_2(arg2)

    @property
    def named_operands(self):
        """Operands that need processing by the name annotator.
        """
        return self.some_children(ShortName)

class Target(Identifier):
    pass

class StackSlot(Integer):
    def consume(self, tokens):
        Integer.consume(self, tokens)
        if self.value < 0:
            raise ParserError(tokens)

# Classes which represent groups of operators in the parse tree

class SimpleOp(NoArgOp):
    @property
    def name(self):
        return self.tokens[0].text

class SimpleFoldLoadOp(SimpleOp):
    may_fold_load = True

class CompareOp(NoArgOp):
    may_fold_load = True

class CondBranchOp(JumpOp):
    may_fold_load = True

# Classes for operators that require specific individual parsing

class AddOp(SimpleFoldLoadOp):
    has_own_handler = True
    name = "add"

class CastOp(NameCastOp):
    def add_child_2(self, type):
        raise_unless_len(type, EXACTLY, 1)
        self.add_child(BasicType).pop_consume(type)

    @property
    def typename(self):
        return self.one_child(BasicType)

class DerefOp(OneArgOp):
    has_own_handler = True
    may_fold_load = True

    def add_folded_load(self, tokens):
        if (len(tokens) == 4
              and isinstance(tokens[1], lexer.OPAREN)
              and isinstance(tokens[3], lexer.CPAREN)):
            # Handle "offset(base)" syntax
            OneArgOp.add_folded_load(self, [tokens[2]])
            OneArgOp.add_folded_load(self, [tokens[0]])
            token = lexer.SyntheticToken(tokens[0], "synthetic add")
            self.add_child(AddOp).consume([token])
        else:
            # Regular folded load
            OneArgOp.add_folded_load(self, tokens)

    def add_children(self, type):
        raise_unless_len(type, EXACTLY, 1)
        self.add_child(BasicType).pop_consume(type)

class DupOp(NoArgOp):
    has_own_handler = True

class GotoOp(JumpOp):
    has_own_handler = True

class LoadOp(OneArgOp):
    has_own_handler = True

    def add_children(self, arg):
        if len(arg) == 1:
            if isinstance(arg[0], lexer.NUMBER):
                klass = Integer
            else:
                for klass in Pointer, Boolean:
                    if arg[0].text in klass.VALUES:
                        break
                else:
                    klass = ShortName
        elif len(arg) == 3:
            klass = FullName
        else:
            raise ParserError(arg)
        self.add_child(klass).consume(arg)

    @property
    def is_offset_base(self):
        return len(list(self.folded_children)) == 2

    @property
    def name(self):
        return self.one_child((ShortName, FullName))

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

class NameOp(NameCastOp):
    def add_child_2(self, newname):
        self.newname = self.add_child(ShortName)
        self.newname.consume(newname)

class OverOp(NoArgOp):
    has_own_handler = True

class PickOp(OneArgOp):
    has_own_handler = True

    def add_children(self, slot):
        self.add_child(StackSlot).consume(slot)

class ReturnOp(NoArgOp):
    has_own_handler = True

class WarnOp(OneArgOp):
    has_own_handler = True

    def add_children(self, text):
        self.add_child(String).consume(text)

# XXX

class Operations(TreeNode):
    CLASSES = {"add": AddOp,
               "cast": CastOp,
               "deref": DerefOp,
               "dup": DupOp,
               "goto": GotoOp,
               "load": LoadOp,
               "name": NameOp,
               "over": OverOp,
               "pick": PickOp,
               "return": ReturnOp,
               "warn": WarnOp}
    for op in ("abs", "drop", "neg", "not", "rot", "swap"):
        CLASSES[op] = SimpleOp
    for op in ("and", "div", "call", "mod", "mul", "or",
               "shl", "shr", "shra", "sub", "xor"):
        CLASSES[op] = SimpleFoldLoadOp
    for op in ("lt", "le", "eq", "ne", "ge", "gt"):
        CLASSES[op] = CompareOp
        CLASSES["b" + op] = CondBranchOp
    del op

    # Do not add an "addr" instruction for DW_OP_addr.  Users
    # should define an "extern ptr" and then "load" it.
    assert "addr" not in CLASSES

    # Do not add a "bra" instruction, it gives no clue as to why
    # it would branch and makes code harder to read.  Users should
    # use "bne NULL" or "bne 0" and let the optimizer figure it out.
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

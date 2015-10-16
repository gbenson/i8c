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

from i8c import I8Error

class I8CError(I8Error):
    """Base class for all compiler errors.
    """
    def __init__(self, msg, prefix="i8c"):
        I8Error.__init__(self, msg, prefix)

class LexerError(I8CError):
    """An error occurred while tokenizing a source file.
    """
    def __init__(self, filename, linenumber, msg):
        I8CError.__init__(self, msg, "%s:%d" % (filename, linenumber))

class LexedError(I8CError):
    """Base class for errors emanating from tokenized source.
    """
    def __init__(self, cause, msg):
        I8CError.__init__(self, msg, cause.fileline)

class ParserError(LexedError):
    """An error occurred while parsing tokens.
    """
    def __init__(self, tokens):
        token = tokens[0]
        LexedError.__init__(self, token, "unexpected ‘%s’" % token.text)

class ParsedError(LexedError):
    """An error occurred while processing the AST.
    """

class NameAnnotatorError(ParsedError):
    """An error occurred annotating the AST with name information.
    """

class TypeAnnotatorError(ParsedError):
    """An error occurred annotating the AST with type information.
    """

class BlockCreatorError(ParsedError):
    """An error occurred creating basic blocks from the AST.
    """

class StackError(ParsedError):
    """The stack is not correct for the requested operation.
    """
    def __init__(self, cause, stack, msg):
        msg = "%s: %s" % (cause.source, msg)
        if stack is not None:
            msg += ":\n" + str(stack)
        ParsedError.__init__(self, cause, msg)

class StackTypeError(StackError):
    """The stack contains incorrect types for the requested operation.
    """
    def __init__(self, cause, stack):
        # Sorry translators...
        types = ["‘%s’" % stack[index].type.name
                 for index in range(cause.arity - 1, -1, -1)]
        if len(types) > 1:
            types[:-1] = [", ".join(types[:-1])]
        types = " and ".join(types)
        msg = "can't %s %s" % (cause.verb, types)
        StackError.__init__(self, cause, stack, msg)

class StackMergeError(StackError):
    def __init__(self, ops, stacks, slot=None):
        from_op, to_op = ops
        prev_stack, new_stack = stacks
        msg = "\narriving from %s with stack:\n%s\n" % (
            from_op.fileline, new_stack)
        msg += "can't merge with previously walked stack:\n%s\n" % prev_stack
        if slot is not None:
            msg += "because of incompatible type at stack[%d]." % slot
        else:
            msg += "because depths differ"
        StackError.__init__(self, to_op, None, msg)

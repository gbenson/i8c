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

from .. import I8Error
from ..compat import fprint
import sys

def warn(msg, cause=None):
    if cause is None:
        prefix = "i8c"
    else:
        prefix = cause.fileline
    fprint(sys.stderr, "%s: warning: %s" % (prefix, msg))

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

class IdentError(ParsedError):
    """An error occurred while processing an identifier.
    """

class UndefinedIdentError(IdentError):
    """The specified identifier was not defined.
    """
    def __init__(self, cause, what, name):
        IdentError.__init__(
            self, cause, "%s ‘%s’ is undefined" % (what, name))

class RedefinedIdentError(IdentError):
    """An attempt was made to redefine an identifier.
    """
    def __init__(self, cause, what, name, prev):
        if prev.is_builtin:
            msg = "definition of ‘%s’ shadows builtin %s" % (name, what)
        else:
            msg = ("definition of ‘%s’ shadows previous\n"
                   "%s: error: %s ‘%s’ was previously defined here") % (
                name, prev.fileline, what, name)
        IdentError.__init__(self, cause, msg)

class ReservedIdentError(IdentError):
    """An attempt was made to define an identifier with a reserved name.
    """
    def __init__(self, cause, what, name):
        IdentError.__init__(
            self, cause, "%s ‘%s’ is reserved" % (what, name))

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

class CastError(StackError):
    """A cast operation is somehow wrong.
    """

class UnnecessaryCastError(CastError):
    """An unnecessary cast was encountered.
    """
    def __init__(self, cause, stack):
        CastError.__init__(self, cause, stack, "unnecessary ‘cast’")

class InvalidCastError(CastError):
    """An invalid cast was encountered.
    """
    def __init__(self, cause, stack, old_type, new_type):
        msg = "can't cast from ‘%s’ to ‘%s’" % (old_type.name,
                                                new_type.name)
        CastError.__init__(self, cause, stack, msg)


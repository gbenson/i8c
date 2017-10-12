# -*- coding: utf-8 -*-
# Copyright (C) 2015-17 Red Hat, Inc.
# This file is part of the Infinity Note Execution Environment.
#
# The Infinity Note Execution Environment is free software; you can
# redistribute it and/or modify it under the terms of the GNU Lesser
# General Public License as published by the Free Software Foundation;
# either version 2.1 of the License, or (at your option) any later
# version.
#
# The Infinity Note Execution Environment is distributed in the hope
# that it will be useful, but WITHOUT ANY WARRANTY; without even the
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with the Infinity Note Execution Environment; if not,
# see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from i8c import I8Error

class I8XError(I8Error):
    """Base class for all runtime errors.
    """
    def __init__(self, msg, prefix="i8x"):
        I8Error.__init__(self, msg, prefix)

class InputFileError(I8XError):
    """An error occurred processing one of our input files.
    """
    def __init__(self, filename, msg):
        I8XError.__init__(self, msg, filename)

class ProviderError(InputFileError):
    """An error occurred processing a note-providing file.
    """

class TestFileError(InputFileError):
    """An error occurred processing a Python test file.
    """

class HeaderFileError(InputFileError):
    """An error occurred processing a C header file.
    """
    def __init__(self, filename, linenumber):
        I8XError.__init__(self,
                          "expected ‘#define NAME VALUE’",
                          "%s:%d" % (filename, linenumber))

class NoteError(I8XError):
    """An error was detected while decoding a note.
    """
    def __init__(self, location, msg):
        args = [self, msg]
        if location is not None:
            args.append("%s[0x%08x]" % (location.srcname,
                                        location.srcoffset))
        I8XError.__init__(*args)

class CorruptNoteError(NoteError):
    """A corrupt note was detected.
    """
    def __init__(self, location, msg=None):
        if msg is None:
            msg = "corrupt note"
        NoteError.__init__(self, location, msg)

class UnhandledNoteError(NoteError):
    """An unhandled note was detected.
    """
    def __init__(self, location, msg=None):
        if msg is None:
            msg = "unhandled note"
        NoteError.__init__(self, location, msg)

class SymbolError(NoteError):
    """No symbols match the referenced address.
    """
    def __init__(self, location, names=None, msg=None):
        if msg is None:
            if names is None:
                msg = "no matching symbols found"
            else:
                msg = ("unresolved symbol %s"
                       % ", ".join("‘%s’" % name for name in names))
        NoteError.__init__(self, location, msg)

class UnresolvedFunctionError(NoteError):
    """The requested function is not present.
    """
    def __init__(self, signature, reference=None):
        if reference is not None:
            reference = reference.src
        NoteError.__init__(self, reference,
                           "unresolved function ‘%s’" % signature)

class ExecutionError(I8XError):
    """An error was detected during bytecode execution.
    """
    def __init__(self, op, msg):
        I8XError.__init__(self, msg, "%s+%04d" % (op.function.signature,
                                                  op.srcoffset))

class BadJumpError(ExecutionError):
    """A DW_OP_bra or DW_OP_skip went to a bad place.
    """
    def __init__(self, op):
        ExecutionError.__init__(self, op, "bad jump")

class BadDerefError(ExecutionError):
    """Something dereferenced an invalid location.
    """
    def __init__(self, op, mem, loc):
        ExecutionError.__init__(
            self, op, "0x%08x: invalid location:\n%s" % (loc, mem))

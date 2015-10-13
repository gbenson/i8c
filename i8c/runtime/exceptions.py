# -*- coding: utf-8 -*-
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

class ELFFileError(InputFileError):
    """An error occurred processing an ELF file.
    """

class TestFileError(InputFileError):
    """An error occurred processing a Python test file.
    """

class HeaderFileError(InputFileError):
    """An error occurred processing a C header file.
    """
    def __init__(self, filename, linenumber):
        I8XError.__init__(self,
                          u"expected ‘#define NAME VALUE’",
                          "%s:%d" % (filename, linenumber))

class NoteError(I8XError):
    """An error was detected while decoding a note.
    """
    def __init__(self, es, msg):
        I8XError.__init__(self, msg, "%s[0x%08x]" % (es.filename, es.start))

class CorruptNoteError(NoteError):
    """A corrupt note was detected.
    """
    def __init__(self, elfslice):
        NoteError.__init__(self, elfslice, "corrupt note")

class UnhandledNoteError(NoteError):
    """An unhandled note was detected.
    """
    def __init__(self, elfslice):
        NoteError.__init__(self, elfslice, "unhandled note")

class FunctionLookupError(I8XError):
    """An error occurred during function lookup.
    """
    def __init__(self, msg, reference=None):
        if reference is None:
            I8XError.__init__(self, msg)
        else:
            I8XError.__init__(self, msg, reference.referrer)

class UndefinedFunctionError(FunctionLookupError):
    """The requested function was not defined.
    """
    def __init__(self, signature, reference=None):
        FunctionLookupError.__init__(
            self, u"undefined function ‘%s’" % signature, reference)

class AmbiguousFunctionError(FunctionLookupError):
    """Multiple copies of the requested function were found.
    """
    def __init__(self, signature, reference=None):
        FunctionLookupError.__init__(
            self, u"function ‘%s’ defined more than once" % signature,
            reference)

class ExecutionError(I8XError):
    """An error was detected during bytecode execution.
    """
    def __init__(self, op, msg):
        I8XError.__init__(self, msg, "%s+%04d" % op.location)

class BadJumpError(ExecutionError):
    """A DW_OP_bra or DW_OP_skip went to a bad place.
    """
    def __init__(self, op):
        ExecutionError.__init__(self, op, "bad jump")

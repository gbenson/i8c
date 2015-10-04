from i8c import I8Error

class I8XError(I8Error):
    """Base class for all runtime errors.
    """
    def __init__(self, msg, prefix="i8x"):
        I8Error.__init__(self, msg, prefix)

class ELFError(I8XError):
    def __init__(self, filename, msg):
        I8XError.__init__(self, msg, filename)

class LocatedError(I8XError):
    def __init__(self, cause, msg):
        I8XError.__init__(self, msg, "%s:0x%x" % cause.location)

class CorruptNoteError(LocatedError):
    def __init__(self, cause):
        LocatedError.__init__(self, cause, "corrupt note")

class UnhandledNoteError(LocatedError):
    def __init__(self, cause):
        LocatedError.__init__(self, cause, "unhandled note")

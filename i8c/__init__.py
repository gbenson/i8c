class I8Error(Exception):
    """Base class for all errors.
    """
    def __init__(self, msg, prefix):
        Exception.__init__(self, prefix + ": error: " + msg)

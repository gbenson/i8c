class I8CError(Exception):
    """Base class for all errors.
    """
    def __init__(self, msg, prefix="i8c"):
        Exception.__init__(self, prefix + ": error: " + msg)

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
        LexedError.__init__(self, token, "unexpected `%s'" % token.text)

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

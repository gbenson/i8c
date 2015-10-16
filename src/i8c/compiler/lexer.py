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

from ..compat import strtoint_c
from . import I8CError, LexerError
import re

TOKEN = re.compile(r"\s+|::|[:,()]|"
                   + r"-?(0x[0-9a-f]+|0[0-7]*|[0-9]+)|"
                   + r"[a-z_][a-z0-9_]*", re.IGNORECASE)

class Token(object):
    def __init__(self, filename, linenumber, text):
        self.filename = filename
        self.linenumber = linenumber
        self.text = text

    @property
    def fileline(self):
        return "%s:%d" % (self.filename, self.linenumber)

    def __str__(self):
        return "%s: %s" % (self.fileline, repr(self.text).lstrip("u"))

class SyntheticToken(Token):
    """A token that the parser inserted.
    """
    def __init__(self, template, text):
        assert isinstance(template, Token)
        Token.__init__(self, template.filename, template.linenumber, text)

class NEWLINE(Token): pass
class COMMA(Token): pass
class OPAREN(Token): pass
class CPAREN(Token): pass
class COLON(Token): pass
class DOUBLE_COLON(Token): pass
class WORD(Token): pass

class NUMBER(Token):
    def __init__(self, *args):
        Token.__init__(self, *args)
        self.value = strtoint_c(self.text, I8CError)

SIMPLE_CLASSES = {
    ",": COMMA,
    "(": OPAREN,
    ")": CPAREN,
    ":": COLON,
    "::": DOUBLE_COLON}

def parse_line_control(line):
    line = line.split()
    return eval(line[2]), int(line[1])

def generate_tokens(readline):
    filename, linenumber = None, 0
    last_token = None
    while True:
        line = readline()
        if not line:
            break
        line = line.decode("utf-8")
        if line.startswith("#"):
            filename, linenumber = parse_line_control(line)
            continue
        while line:
            match = TOKEN.match(line)
            if match is None:
                raise LexerError(filename, linenumber,
                                 "invalid syntax: ‘%s’" % line.rstrip())
            tokentext = match.group(0)
            assert len(tokentext) > 0
            assert line.startswith(tokentext)
            line = line[len(tokentext):]
            klass = SIMPLE_CLASSES.get(tokentext, None)
            if klass is None:
                if tokentext[0].isspace():
                    if (not (last_token is None
                             or isinstance(last_token, NEWLINE))
                        and "\n" in tokentext):
                        klass = NEWLINE
                elif tokentext[0] == "-" or tokentext[0].isdigit():
                    klass = NUMBER
                else:
                    klass = WORD
            if klass is not None:
                last_token = klass(filename, linenumber, tokentext)
                yield last_token
            # Hack to allow labels on the same line as operations.
            if klass is COLON:
                last_token = NEWLINE(filename, linenumber, "synthetic")
                yield last_token
        linenumber += 1

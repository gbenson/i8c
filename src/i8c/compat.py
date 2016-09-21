# -*- coding: utf-8 -*-
# Copyright (C) 2015-16 Red Hat, Inc.
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

import sys

if sys.version_info < (3,):
    str = unicode
    integer = (int, long,)
    next = lambda i: i.next()
    join_bytes = lambda seq: "".join(c.decode("iso-8859-1")
                                     for c in seq).encode("iso-8859-1")
else:
    str = str
    integer = (int,)
    next = next
    join_bytes = bytes

def fprint(file, text=""):
    fwrite(file, text + "\n")

def fwrite(file, text):
    if sys.version_info < (3,):
        text = text.encode(getattr(file, "encoding", None) or "utf-8",
                           "replace")
    file.write(text)

def strtoint_c(text, exception):
    if text.startswith("-"):
        sign, unsigned = "-", text[1:]
    else:
        sign, unsigned = "", text
    if (len(unsigned) > 1 and unsigned[0] == "0"):
        if unsigned[1] in "oO":
            unsigned = "BadOctal" # Force exception
        elif unsigned[1] not in "xX":
            unsigned = "0o" + unsigned[1:]
    try:
        return int(sign + unsigned, 0)
    except ValueError:
        raise exception("invalid integer literal ‘%s’" % text)

if sys.version_info < (3, 3):
    from imp import load_source as load_module_from_source
else:
    from importlib.machinery import SourceFileLoader

    def load_module_from_source(name, filename):
        return SourceFileLoader(name, filename).load_module()


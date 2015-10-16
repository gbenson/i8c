# -*- coding: utf-8 -*-
# Copyright (C) 2015 Red Hat, Inc.
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
else:
    str = str
    integer = (int,)
    next = next

def fprint(file, text=""):
    fwrite(file, text + "\n")

def fwrite(file, text):
    if sys.version_info < (3,):
        text = text.encode(getattr(file, "encoding", "utf-8"))
    file.write(text)

def strtoint_c(text, exception):
    if text in ("0", "-0"):
        return 0
    if not text.startswith("0o"):
        if text.startswith("0") and not text.startswith("0x"):
            text = "0o" + text[1:]
        elif text.startswith("-0") and not text.startswith("-0x"):
            text = "-0o" + text[2:]
        try:
            return int(text, 0)
        except ValueError:
            pass
    raise exception("invalid integer literal: " + text)

if sys.version_info < (3, 3):
    from imp import load_source as load_module_from_source
else:
    from importlib.machinery import SourceFileLoader

    def load_module_from_source(name, filename):
        return SourceFileLoader(name, filename).load_module()


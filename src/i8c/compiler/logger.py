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

from ..compat import fwrite
import sys

class Logger(object):
    def __init__(self):
        self.is_enabled = False

    def disable(self):
        self.is_enabled = False

    def enable(self):
        self.is_enabled = True

    def __call__(self, msg):
        if self.is_enabled:
            sys.stderr.write(msg)

loggers = {}

def debug_printer_for(module):
    global loggers
    faculty = module.split(".")[-1]
    logger = loggers.get(faculty, None)
    if logger is None:
        logger = loggers[faculty] = Logger()
    return logger

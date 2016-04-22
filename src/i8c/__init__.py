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

class I8Error(Exception):
    """Base class for all errors.
    """
    def __init__(self, msg, prefix):
        Exception.__init__(self, prefix + ": error: " + msg)

def version():
    try:
        import pkg_resources
        return pkg_resources.get_distribution("i8c").version
    except: # pragma: no cover
        # This block is excluded from coverage because while
        # we could test it (by hiding the egg-info somehow?)
        # it seems like a lot of effort for very little gain.
        return "UNKNOWN"

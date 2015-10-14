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

from . import version

def version_message_for(program, (license_txt, license_url)):
    license_url = "<%s>" % license_url
    return """\
%s %s
Copyright (C) 2015 Red Hat, Inc.
License %s\n  %s
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.""" % (
        (program, version(), license_txt, license_url))

def usage_message_footer():
    return """

Home page: <https://pypi.python.org/pypi/i8c/>
Bug tracker: <https://github.com/gbenson/i8c/issues/>"""

# -*- coding: utf-8 -*-
from . import version

def version_message_for(program):
    return """\
GNU %s %s
Copyright (C) 2015 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.""" % (program,
                                                            version())

def usage_message_footer():
    return """

Home page: <https://pypi.python.org/pypi/i8c/>
Bug tracker: <https://github.com/gbenson/i8c/issues/>"""

# -*- coding: utf-8 -*-
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

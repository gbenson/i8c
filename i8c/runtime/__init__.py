# -*- coding: utf-8 -*-
from .exceptions import *
from .context import Context
from .testcase import TestCase
import sys

def main():
    from .driver import main
    try:
        main(sys.argv[1:])
    except I8XError as e:
        print >>sys.stderr, unicode(e).encode("utf-8")
        return 1

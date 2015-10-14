# -*- coding: utf-8 -*-
from .exceptions import *
from .logger import loggers
import sys

def compile(readline, write):
    from .driver import compile
    return compile(readline, write)

def main():
    from .driver import main
    try:
        main(sys.argv[1:])
    except I8CError as e:
        print >>sys.stderr, unicode(e).encode("utf-8")
        return 1

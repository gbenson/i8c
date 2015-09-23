import sys

def run_compiler():
    from i8c import compiler
    from i8c import exceptions
    try:
        compiler.main(sys.argv[1:])
    except exceptions.I8CError as e:
        print >>sys.stderr, e
        sys.exit(1)

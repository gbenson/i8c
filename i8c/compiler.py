from i8c import blocks
from i8c import emitter
from i8c import lexer
from i8c import names
from i8c import optimizer
from i8c import parser
from i8c import serializer
from i8c import stack
from i8c import types
from i8c.exceptions import I8CError
from i8c.logger import loggers
import subprocess
import sys

def compile(readline, write):
    tree = parser.build_tree(lexer.generate_tokens(readline))
    tree.accept(names.NameAnnotator())
    tree.accept(types.TypeAnnotator())
    tree.accept(blocks.BlockCreator())
    tree.accept(stack.StackWalker())
    tree.accept(optimizer.BlockOptimizer())
    tree.accept(serializer.Serializer())
    tree.accept(optimizer.StreamOptimizer())
    tree.accept(emitter.Emitter(write))

class CommandLine(object):
    def __init__(self, args):
        self.with_cpp = True
        self.with_asm = True
        self.cpp_args = []
        self.asm_args = []
        self.__process_args(args)

    def __process_args(self, args):
        while args:
            arg = args.pop(0)
            if arg == "-o":
                if not args:
                    raise I8CError("missing filename after `-o'")
                # GCC doesn't complain about multiple "-o"
                # options, it just uses the last one it saw.
                self.asm_args.append(arg)
                self.asm_args.append(args.pop(0))
            elif arg.startswith("-o"):
                self.asm_args.append(arg)
            elif arg.endswith(".i8") and not arg.startswith("-"):
                if self.asm_args and self.asm_args[-1] == "-include":
                    self.asm_args.pop()
                self.cpp_args.append(arg)
            elif arg.startswith("-8"):
                # Our options all start with "-8"
                if arg == "-8no-cpp":
                    self.with_cpp = False
                elif arg == "-8no-asm":
                    self.with_asm = False
                elif arg.startswith("-8debug"):
                    if arg == "-8debug":
                        arg += "=all"
                    for faculty in arg[8:].split(","):
                        self.__enable_logging(faculty)
                else:
                    raise I8CError("unrecognized option `%s'" % arg)
            else:
                self.cpp_args.append(arg)
                self.asm_args.append(arg)

    def __enable_logging(self, faculty):
        if faculty == "all":
            for logger in loggers.values():
                logger.enable()
        else:
            loggers[faculty].enable()

def setup_input(args):
    if not args.with_cpp:
        return None, sys.stdin
    command = ["gcc", "-E", "-x", "c"] + args.cpp_args
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    return process, process.stdout

def setup_output(args):
    if not args.with_asm:
        return None, sys.stdout
    command = ["gcc", "-c", "-x", "assembler-with-cpp", "-"] + args.asm_args
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    return process, process.stdin

def main(args):
    args = CommandLine(args)
    cpp, infile = setup_input(args)
    asm, outfile = setup_output(args)
    compile(infile.readline, outfile.write)
    if cpp is not None:
        infile.close()
        cpp.wait()
    if asm is not None:
        outfile.close()
        asm.wait()

# -*- coding: utf-8 -*-
# Copyright (C) 2015-17 Red Hat, Inc.
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

from .. import cmdline
from ..compat import fprint
from . import blocks
from . import commands
from . import emitter
from . import externals
from . import I8CError
from . import lexer
from . import loggers
from . import names
from . import optimizer
from . import parser
from . import serializer
from . import stack
from . import target
from . import types
import copy
import io
import os
import subprocess
import sys

USAGE = """\
Usage: i8c [OPTION]... [FILE]...

Infinity Note Compiler.

Options:
  --help     Display this information.
  --version  Display version information.
  -E         Preprocess only; do not compile, assemble or link.
  -S         Compile only; do not assemble or link.
  -c         Compile and assemble, but do not link.
  -fpreprocessed
             Do not preprocess.
  --wrap-asm
             Wrap ‘-S’ output in C ‘asm’ statements.
  -o FILE    Place the output into FILE.

Note that I8C uses GCC both to preprocess its input (unless invoked
with ‘-fpreprocessed’) and to assemble its output (unless invoked with
‘-E’ or ‘-S’).  If GCC is used, all options not explicitly listed
above will be passed to GCC unmodified.

In general I8C operates like GCC, so if you’re used to GCC then I8C
should make sense.  Try it!

In most cases the command you want is ‘i8c -c file.i8’, which reads
and compiles ‘file.i8’ and writes the result to ‘file.o’.""" \
    + cmdline.usage_message_footer_for("I8C")

LICENSE = ("GPLv3+: GNU GPL version 3 or later",
           "http://gnu.org/licenses/gpl-3.0.html")

class CommandLine(object):
    def __init__(self, args):
        self.cpp_cmd = commands.Preprocessor()
        self.asm_cmd = commands.Assembler()

        self.showinfo = None
        self.with_cpp = True
        self.with_i8c = True
        self.with_asm = True
        self.infiles = []
        self.outfile = None
        self.cpp_args = []
        self.asm_args = []
        self.wrap_asm = False
        self.__process_args(args)

    def __process_args(self, args):
        args = copy.copy(list(args))
        while args:
            arg = args.pop(0)

            # --help     Display usage information
            # --version  Display version information
            #
            # Both these options cause us to print information and
            # exit immediately, without continuing to process the
            # command line or compiling anything.
            if arg == "--help":
                self.showinfo = USAGE
                return

            elif arg == "--version":
                self.showinfo = cmdline.version_message_for("I8C", LICENSE)
                return

            # -E  Preprocess only; do not compile, assemble or link
            # -S  Compile only; do not assemble or link
            # -c  Compile and assemble, but do not link
            # -fpreprocessed
            #     Indicate to the preprocessor that the input file
            #     has already been preprocessed.
            #
            # These options control what processes we run.  GCC
            # doesn't seem to care if you specify more than one of
            # these so we don't either.
            elif arg == "-E":
                self.with_i8c = False
                self.with_asm = False

            elif arg == "-S":
                self.with_asm = False

            elif arg == "-c":
                self.asm_args.append(arg)

            elif arg == "-fpreprocessed":
                self.with_cpp = False

            elif arg == "--wrap-asm":
                self.wrap_asm = True

            # -o <file>  Place the output into <file>
            #
            # GCC doesn't complain about multiple "-o" options,
            # it just uses the last one it saw, so we do too.
            elif arg == "-o":
                if not args:
                    raise I8CError("missing filename after ‘-o’")

                self.asm_args.append(arg)
                self.outfile = args.pop(0)
                self.asm_args.append(self.outfile)

            elif arg.startswith("-o"):
                self.asm_args.append(arg)
                self.outfile = arg[2:]

            # -include <file>
            #     Process file as if ‘#include "file"’ appeared
            #     as the first line of the primary source file.
            elif arg == "-include":
                if not args:
                    raise I8CError("missing filename after ‘-include’")

                self.cpp_args.append(arg)
                arg = args.pop(0)
                self.infiles.append(arg)
                self.cpp_args.append(arg)

            # Input filenames.  Not so easy to distinguish.
            elif (arg.endswith(".i8")
                  or arg.endswith(".i8p")) and not arg.startswith("-"):
                self.infiles.append(arg)
                self.cpp_args.append(arg)

            # -x <language>  Specify the language of input files
            #
            # Don't allow users to specify this, we need to use
            # it ourselves.
            elif arg.startswith("-x"):
                raise I8CError("unrecognized option ‘%s’" % arg)

            # --debug[=faculty1[,faculty2]...]
            #
            # Turn on debugging for some or all of i8c.
            elif arg.startswith("--debug"):
                if arg == "--debug":
                    for logger in loggers.values():
                        logger.enable()
                else:
                    for faculty in arg[8:].split(","):
                        logger = loggers.get(faculty, None)
                        if logger is not None:
                            logger.enable()

            # All other options get passed through to both the
            # preprocessor and the assembler, if they are used.
            else:
                self.cpp_cmd.args.append(arg)
                self.asm_cmd.args.append(arg)

def setup_input(args):
    process = infile = None
    if args.with_cpp:
        extra_args = args.cpp_args
        process = args.cpp_cmd.Popen(extra_args, stdout=subprocess.PIPE)
        infile = process.stdout
    elif args.infiles in ([], ["-"]):
        infile = sys.stdin
    elif len(args.infiles) == 1:
        infile = open(args.infiles[0], "rb")
    else:
        infile = io.BytesIO()
        for filename in args.infiles:
            with open(filename, "rb") as fp:
                infile.write(fp.read())
        infile.seek(0)
    return process, infile

def guess_outfile(args):
    assert args.outfile is None
    if args.with_asm:
        assert "-c" in args.asm_args
        ext = ".o"
    elif args.wrap_asm:
        ext = ".c"
    else:
        ext = ".S"
    if len(args.infiles) != 1:
        raise I8CError("unable to determine output filename")
    root = os.path.splitext(args.infiles[0])[0]
    return root + ext

def setup_output(args):
    if args.with_asm:
        extra_args = ["-x", "assembler-with-cpp"] + args.asm_args + ["-"]
        if args.outfile is None and "-c" in args.asm_args:
            extra_args.extend(("-o", guess_outfile(args)))
        process = args.asm_cmd.Popen(extra_args, stdin=subprocess.PIPE)
        outfile = process.stdin
    else:
        process = None
        filename = args.outfile
        if filename is None:
            if args.with_i8c:
                filename = guess_outfile(args)
            else:
                filename = "-"
        if filename == "-":
            outfile = sys.stdout
        else:
            outfile = open(filename, "wb")
    return process, outfile

def compile(readline, write, commandline=None, wrap_asm=None):
    if wrap_asm is None:
        wrap_asm = getattr(commandline, "wrap_asm", False)

    tree = parser.build_tree(lexer.generate_tokens(readline))
    tree.accept(target.TargetAnnotator(commandline))
    tree.accept(types.TypeAnnotator())
    tree.accept(names.NameAnnotator())
    tree.accept(externals.PerFileTableCreator())
    tree.accept(externals.PerFuncTableCreator())
    tree.accept(blocks.BlockCreator())
    tree.accept(stack.StackWalker())
    tree.accept(optimizer.BlockOptimizer())
    tree.accept(serializer.Serializer())
    tree.accept(optimizer.StreamOptimizer())
    tree.accept(emitter.Emitter(write, wrap_asm))
    return tree

def main(args):
    args = CommandLine(args)
    if args.showinfo is not None:
        fprint(sys.stdout, args.showinfo)
        return

    clue = "Try ‘i8c --help’ for more information."
    if ((args.with_cpp and not args.cpp_args)
            or not (args.with_cpp or args.with_i8c or args.with_asm)):
        raise I8CError("nothing to do!\n%s" % clue)

    outfile = io.BytesIO()
    process, infile = setup_input(args)
    try:
        if args.with_i8c:
            compile(infile.readline, outfile.write, args)
        else:
            outfile.write(infile.read())
    finally:
        if infile is not sys.stdin:
            infile.close()
        if process is not None:
            process.wait()
            if process.returncode != 0:
                return process.returncode
    outfile.seek(0)
    infile = outfile

    process, outfile = setup_output(args)
    try:
        data = infile.read()
        if outfile is sys.stdout:
            data = data.decode("utf-8")
        outfile.write(data)
    finally:
        if outfile is not sys.stdout:
            outfile.close()
        if process is not None:
            process.wait()
            if process.returncode != 0:
                return process.returncode

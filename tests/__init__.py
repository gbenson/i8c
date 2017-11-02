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

from i8c.compiler import commands
from i8c import compiler
from i8c import runtime
from i8c import version
from i8c.runtime import coverage
from i8c.runtime import memory
from i8c.runtime import pythonctx
from i8c.runtime.core import TestObject
from i8c.runtime.testcase import BaseTestCase
import collections
import copy
import glob
import io
import operator
import os
import struct
import subprocess
import sys
import threading
import weakref
from functools import reduce

class TestCompiler(TestObject):
    I8C_KWARGS = {}

    def compile(self, *args, **kwargs):
        """See TestCase.compile.__doc__.
        """
        result = self.env._new_compilation()
        runner = CompilerTask(result.fileprefix)
        for variant in runner.run(self, *args, **kwargs):
            result.add_variant(variant)
        return result

    def setup_build(self, build):
        """Setup the build prior to compilation.
        """

    def preprocess(self, build, input):
        """Preprocess the I8Language input ready for I8C.
        """
        result = ['# 1 "%s"\n' % build.i8c_input_file,
                  "wordsize %d\n" % build.wordsize]
        while True:
            start = input.find("//")
            if start < 0:
                break
            result.append(input[:start])
            limit = input.find("\n", start)
            if limit < start:
                break
            input = input[limit:]
        result.append(input)
        return "".join(result)

    def i8compile(self, build, input, **kwargs):
        """See TestCase.i8compile.__doc__.
        """
        return self.env.i8compile(input, **kwargs)

    def postprocess(self, build, output):
        """Postprocess the output of I8C ready for assembly.
        """
        return output

    def link(self, build, assembler, objfiles):
        """Link the assembler output into the final format.
        """
        assert len(objfiles) == 1
        return objfiles[0]

    def postlink(self, build, assembler, linked):
        """Postprocess the linked file.
        """
        return linked

class SoftFailure(Exception):
    pass

class CompilerTask(object):
    __filenames = {}
    __filenames_lock = threading.Lock()

    __parallelize = os.environ.get("I8CTEST_PARALLEL", "") == "1"

    def __init__(self, fileprefix):
        self.__fileprefix = fileprefix
        self.__result = None
        self.__exception = None
        self.__extra_sources = ()

    def __unique_filename(self, ext, is_writable):
        """Return a unique filename with the specified extension.
        """
        filename = self.__fileprefix + ext
        with self.__filenames_lock:
            assert filename not in self.__filenames
            self.__filenames[filename] = is_writable
        return filename

    def readonly_filename(self, ext):
        """Return a unique filename with the specified extension.

        This method should be used to generate names for files that
        will be created by external programs.
        """
        return self.__unique_filename(ext, False)

    def writable_filename(self, ext):
        """Return a unique filename with the specified extension.

        This method should be used to generate names for files that
        will be created using CompilerTask.write_file.
        """
        return self.__unique_filename(ext, True)

    def write_file(self, text, filename):
        """Write data to a file with a unique filename.
        """
        with self.__filenames_lock:
            assert self.__filenames.get(filename, False)

        outdir = os.path.dirname(filename)
        try:
            os.makedirs(outdir)
        except OSError:
            pass
        with open(filename, "w") as fp:
            fp.write(text)

        with self.__filenames_lock:
            self.__filenames[filename] = True

    def add_sourcefile(self, filename):
        """Add an extra input file for the assembler.
        """
        self.__extra_sources += (filename,)

    def __objfile_filename_for(self, srcfile):
        """Return the object filename for an assembler input file.
        """
        outdir = os.path.dirname(self.__fileprefix)
        srcdir, srcbase = os.path.split(srcfile)
        if srcdir == outdir:
            prefix = os.path.commonprefix((self.__fileprefix, srcfile))
            prefix = ".".join(srcfile[len(prefix):].split(".")[:-1])
            if prefix and prefix[0] not in "-_.":
                prefix = "_" + prefix
        else:
            prefix = self.__fileprefix + os.path.splitext(srcbase)[0]
        return self.readonly_filename(prefix + ".o")

    def __fork(self, func, variants, *args, **kwargs):
        """Call func once per variant with a copy of self.
        """
        children, threads = [], []
        for variant in variants:
            if not isinstance(variant, collections.Sequence):
                variant = (variant,)
            child = copy.copy(self)
            children.append(child)
            thread = threading.Thread(None, child.__fork_child, None,
                                      (func,) + args + variant, kwargs)
            threads.append(thread)

        if self.__parallelize:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        else:
            for thread in threads:
                thread.run()

        results = []
        for child in children:
            if child.__exception is not None:
                raise child.__exception
            results.extend(child.__result)
        return results

    def __fork_child(self, func, *args, **kwargs):
        assert self.__result is None
        assert self.__exception is None
        try:
            self.__result = func(self, *args, **kwargs)
        except SoftFailure:
            self.__result = []
        except Exception as e:
            self.__exception = e

    def run(self, tc, *args, **kwargs):
        tc.setup_build(self)
        return self.__fork(CompilerTask.__stage_1,
                           tc.env.assemblers.by_wordsize,
                           tc, *args, **kwargs)

    def __stage_1(self, tc, input, wordsize, assemblers):
        assert not hasattr(self, "wordsize")
        self.wordsize = wordsize
        self.__fileprefix += "_%d" % self.wordsize

        self.i8c_input_file = self.writable_filename(".i8")
        i8c_input = tc.preprocess(self, input)
        self.write_file(i8c_input, self.i8c_input_file)

        self.syntax_tree, i8c_output = tc.i8compile(self, i8c_input,
                                                    **tc.I8C_KWARGS)

        ext = i8c_output.startswith("__asm__") and ".c" or ".S"
        self.asm_input_file = self.writable_filename(ext)
        asm_input = tc.postprocess(self, i8c_output)
        self.write_file(asm_input, self.asm_input_file)

        return self.__fork(CompilerTask.__stage_2, assemblers, tc)

    def __stage_2(self, tc, assembler):
        assert not hasattr(self, "byteorder")
        self.byteorder = assembler.output_byteorder
        self.__fileprefix += {b"<": "el", b">": "be"}[self.byteorder]

        check, arch = assembler._TestAssembler__machine_name.split("_", 1)
        assert self.__fileprefix.endswith("_" + check)
        self.__fileprefix += "_" + arch

        srcfiles = (self.asm_input_file,) + self.__extra_sources
        objfiles = []
        for srcfile in srcfiles:
            objfile = self.__objfile_filename_for(srcfile)
            assembler.check_call(("-c", srcfile, "-o", objfile))
            objfiles.append(objfile)

        linked = tc.link(self, assembler, objfiles)
        self.asm_output_file = tc.postlink(self, assembler, linked)

        return (self,)

class TestAssembler(commands.Assembler):
    def __check_call(self, *args, **kwargs):
        return super(TestAssembler, self).check_call(*args, **kwargs)

    def check_call(self, *args, **kwargs):
        fail_softly = kwargs.pop("fail_softly", False)
        if not fail_softly or self.__is_principal:
            return self.__check_call(*args, **kwargs)

        with open(os.devnull, "w") as fp:
            kwargs["stderr"] = fp
            try:
                return self.__check_call(*args, **kwargs)
            except subprocess.CalledProcessError:
                print("  SOFT FAILURE:", self.__machine_name)
                raise SoftFailure

class AssemblerManager(object):
    def __init__(self):
        self.__variants = {}
        self.__order = []
        self.__by_wordsize = {}

        self.__add_principal()
        self.__try_add_alternates()

        # Sort self.__by_wordsize such that the first machine of
        # the first wordsize is the principal (i.e. I8C_AS with no
        # alternate wordsize.)
        principal_wordsize = self.__variants[self.__order[0]].output_wordsize
        tmp = sorted((ws != principal_wordsize, ws, tuple(machs))
                     for ws, machs in self.__by_wordsize.items())
        self.__by_wordsize = tuple((ws, machs) for sk, ws, machs in tmp)
        for index, variant in enumerate(self):
            assert variant._TestAssembler__is_principal == (index == 0)

    def __len__(self):
         return len(self.__variants)

    def __iter__(self):
        for wordsize, machines in self.__by_wordsize:
            for machine in machines:
                yield self.__variants[machine]

    def __getitem__(self, key):
        return tuple(self)[key]

    @property
    def by_wordsize(self):
        for wordsize, machines in self.__by_wordsize:
            yield wordsize, (self.__variants[machine]
                             for machine in machines)

    def announce(self, file=sys.stderr):
        notetypes = {}
        for machine in self.__order:
            notetype, arch = machine.split("_", 1)
            print("building %s (%s)" % (notetype, arch), file=file)
            notetypes[notetype] = True
        notetypes = notetypes.keys()
        message = "testing " + ", ".join(sorted(notetypes))
        looksgood = len(notetypes) == 4
        if not looksgood:
            message = "warning: %s only!" % message
        if hasattr(file, "isatty") and file.isatty():
            colour = looksgood and 32 or 33
            message = "\x1B[%dm%s\x1B[0m" % (colour, message)
        print(message, file=file)

    def __add_principal(self):
        self.__add_variant()

    def __try_add_alternates(self, prefix="I8CTEST_ALT_AS"):
        keys = (key for key in os.environ.keys() if key.startswith(prefix))
        for key in sorted(keys):
            self.__try_add_variant(os.environ[key].split())

    def __try_add_variant(self, *args, **kwargs):
        kwargs["probe_quietly"] = True
        try:
            return self.__add_variant(*args, **kwargs)
        except:
            pass

    def __add_variant(self, *args, **kwargs):
        is_alt_wordsize = kwargs.pop("is_alt_wordsize", False)
        is_alt_byteorder = kwargs.pop("is_alt_byteorder", False)

        variant = TestAssembler(*args, **kwargs)
        wordsize = variant.output_wordsize
        machine = "%d%s" % (wordsize,
                            {b"<": "el",
                             b">": "be"}[variant.output_byteorder])

        e_machine = variant.output_e_machine
        if e_machine.startswith("EM_"):
            e_machine = e_machine[3:].lower()
        machine += "_" + e_machine

        machine = {"32el_386": "32el_i386",
                   "32el_ppc": "32el_ppc32le",
                   "32el_x86_64": "32el_x32",
                   "64be_s390": "64be_s390x",
                   "64el_ppc64": "64el_ppc64le",
            }.get(machine, machine)

        assert machine not in self.__variants
        variant._TestAssembler__is_principal = not self.__variants
        variant._TestAssembler__machine_name = machine
        self.__order.append(machine)
        self.__variants[machine] = variant
        if wordsize not in self.__by_wordsize:
            self.__by_wordsize[wordsize] = []
        self.__by_wordsize[wordsize].append(machine)

        if not is_alt_wordsize:
            self.__try_add_alt_wordsize(variant, is_alt_byteorder)
            if not is_alt_byteorder:
                self.__try_add_alt_byteorder(variant, is_alt_wordsize)

        return variant

    def __try_add_alt_wordsize(self, main, is_alt_byteorder):
        for try_wordsize in (64, 32, 31):
            elf_wordsize = ((try_wordsize + 1) >> 1) << 1
            if main.output_wordsize == elf_wordsize:
                continue
            try_args = main.args + ["-m%d" % try_wordsize]
            if self.__try_add_variant(try_args,
                                      is_alt_wordsize=True,
                                      is_alt_byteorder=is_alt_byteorder):
                return

    def __try_add_alt_byteorder(self, main, is_alt_wordsize):
        try_byteorder = {b"<": "big",
                         b">": "little"}[main.output_byteorder]
        try_args = main.args + ["-m" + try_byteorder]
        self.__try_add_variant(try_args,
                               is_alt_wordsize=is_alt_wordsize,
                               is_alt_byteorder=True)

class TestContext(object):
    @classmethod
    def with_backend(cls, backend_cls):
        backend = backend_cls.INTERPRETER.split(None, 1)[0].lower()
        clsname = backend + "_TestContext"
        if sys.version_info < (3,):
            clsname = clsname.encode("utf-8")
        return type(clsname, (cls, backend_cls), {"backend": backend})

    @property
    def _i8ctest_bad_wordsize_msg(self):
        """Called by import_notes if self.MAX_WORDSIZE too small."""
        self.is_testable = False
        return "unsupported wordsize (%d bits max)" % self.MAX_WORDSIZE

    def __init__(self, testcase, compilertask):
        super(TestContext, self).__init__(testcase)
        testcase.addCleanup(self.finalize)
        self.build = compilertask
        # Load the notes from it
        self.coverage = coverage.Accumulator()
        self.import_error = None
        self.is_testable = True
        testcase.addCleanup(delattr, self, "import_error")
        try:
            self.import_notes(self.build.asm_output_file)
        except runtime.NoteError as e:
            self.import_error = e
            return
        self.notes = list(self._i8ctest_functions)
        testcase.addCleanup(delattr, self, "notes")
        # Make sure we got at least one note
        testcase.assertGreaterEqual(len(self.notes), 1)
        # Setup for note execution
        testcase._install_user_functions(self)
        self.memory = memory.Memory(testcase)

    @property
    def note(self):
        if self.import_error is not None:
            raise self.import_error
        assert len(self.notes) == 1
        return self.notes[0]

    @property
    def ops(self):
        ops = sorted(self.note.ops.items())
        return [op for pc, op in ops]

    @property
    def opnames(self):
        return [op.name for op in self.ops]

class Multiplexer(TestObject):
    def __init__(self, env):
        super(Multiplexer, self).__init__(env)
        for name in getattr(self, "MULTIPLEXED_FIELDS", ()):
            self.add_multiplexed_property(name)

    def add_multiplexed_property(self, name):
        splitname = name.split(".")
        parent = self
        for attr in splitname[:-1]:
            parent = getattr(parent, attr)
        attr = splitname[-1]
        assert not hasattr(parent, attr)
        setattr(parent, attr, MultiplexedProperty(self, splitname))

    def assertHasVariants(self):
        self.env.assertGreater(len(self.variants), 0)

    def assertInVariants(self, variant):
        for check in self.variants:
            if variant == check:
                return
        self.env.fail("%s not in %s" % (variant, self.variants))

    def all_values_of(self, multiplexed):
        self.env.assertIs(multiplexed.mux, self)
        self.assertHasVariants()
        return (multiplexed.value_in(variant)
                for variant in self.variants)

    def map_call(self, func, *args, **kwargs):
        self.env.assertTrue(isinstance(func, Multiplexed))
        self.env.assertIs(func.mux, self)
        self.assertHasVariants()
        return (func.call_in(variant, *args, **kwargs)
                for variant in self.variants)

class Multiplexed(TestObject):
    def __init__(self, mux):
        super(Multiplexed, self).__init__(mux.env)
        self.__mux = weakref.ref(mux)

    @property
    def mux(self):
        return self.__mux()

    def __demux(self, values, name=None):
        self.mux.assertHasVariants()
        values = list(values)
        self.env.assertEqual(len(values), len(self.mux.variants))
        result = values[0]
        all_equal = [result] * len(values)
        if name is None:
            # Caller expects a single value.
            self.env.assertEqual(values, all_equal)
        elif values != all_equal:
            # Return multiplexed result.
            result = self.__maybe_unwrap(MultiplexedValue(self.mux,
                                                          name, values))
        return result

    # Value accessors.

    @property
    def all_values(self):
        return self.mux.all_values_of(self)

    # Truth checking.

    def __bool__(self):
        return not self.__demux(map(operator.not_, self.all_values))

    if sys.version_info < (3,):
        __nonzero__ = __bool__
        del __bool__

    # Comparisons.

    def __eq__(self, other):
        # Compare values individually if possible.
        if isinstance(other, Multiplexed):
            svalues = list(self.all_values)
            ovalues = list(other.all_values)
            if len(ovalues) == len(svalues):
                for sval, oval in zip(svalues, ovalues):
                    if oval != sval:
                        return False
                return True

        # Demultiplex and compare if not.
        return not (self != other)

    def __ne__(self, other):
        return self.__demux(self.all_values) != other

    # Sequence access.

    def __len__(self):
        return self.__demux(map(len, self.all_values))

    def __getitem__(self, key):
        return self.__demux((value[key] for value in self.all_values),
                            "%s[%s]" % (self.display_name, key))

    @staticmethod
    def __maybe_unwrap(ob):
        """Attempt to unwrap multiplexed sequences into regular ones.

        If ob is a multiplexed value, and all its values are sequences
        with the same length, then return a regular sequence (a list
        to be specific) in which some or all values will be
        multiplexed values.  Note that this is recursive; the result
        will never contain multiplexed sequences.

        If ob is not a multiplexed sequence then return ob unchanged.
        """
        if not isinstance(ob, Multiplexed):
            return ob
        try:
            length = len(ob)
        except:
            return ob
        return [Multiplexed.__maybe_unwrap(ob[i])
                for i in range(length)]

    # Method invocation.

    def __call__(self, *args, **kwargs):
        return self.__demux(self.mux.map_call(self, *args, **kwargs),
                            "<%s() result>" % self.display_name)

    def call_in(self, variant, *args, **kwargs):
        func = self.value_in(variant)
        args = tuple(self.__resolve_in(variant, arg)
                     for arg in args)
        kwargs = dict((key, self.__resolve_in(variant, value))
                      for key, value in kwargs.items())
        with self.env._install_context(variant):
            return func(*args, **kwargs)

    @staticmethod
    def __resolve_in(variant, value):
        if isinstance(value, Multiplexed):
            value = value.value_in(variant)
        return value

class MultiplexedProperty(Multiplexed):
    def __init__(self, mux, splitname):
        super(MultiplexedProperty, self).__init__(mux)
        self.__splitname = tuple(splitname)

    @property
    def display_name(self):
        return ".".join(self.__splitname)

    def value_in(self, variant):
        self.mux.assertInVariants(variant)
        for attr in self.__splitname:
            variant = getattr(variant, attr)
        return variant

class MultiplexedValue(Multiplexed):
    def __init__(self, mux, name, values):
        super(MultiplexedValue, self).__init__(mux)
        self.env.assertEqual(len(values), len(self.mux.variants))
        self.display_name = name
        self.__values = values

    def value_in(self, variant):
        self.mux.assertInVariants(variant)
        return self.__values[self.mux.variants.index(variant)]

class TestOutput(Multiplexer):
    MULTIPLEXED_FIELDS = (
        "call",
        "coverage",
        "coverage.functions",
        "note",
        "note.signature",
        "opnames",
        "ops",
        "to_signed",
        "to_unsigned",
        "tracelevel",
    )

    backends = []
    for backend in (runtime.Context, pythonctx.Context):
        if backend not in backends:
            backends.append(backend)
        del backend
    backends = list(map(TestContext.with_backend, backends))

    @classmethod
    def announce(cls, file=sys.stderr):
        backends = getattr(cls, "backends", ())
        if len(backends) == 1:
            format = "warning: using %s only!"
            looksgood = False
        else:
            format = "using %s"
            looksgood = "libi8x" in (cc.backend for cc in backends)
        if hasattr(file, "isatty") and file.isatty():
            colour = looksgood and 32 or "1;31"
            format = "\x1B[%sm%s\x1B[0m" % (colour, format)
        for cc in backends:
            print(format % cc.INTERPRETER, file=file)

    def __init__(self, env, fileprefix):
        super(TestOutput, self).__init__(env)
        self.fileprefix = fileprefix
        self.variants = []

    # TestCase.compile historically returned a two-element tuple
    # of (AST, TestOutput).  Defining __iter__ like this allows
    # TestCase.compile to return just TestOutput without having
    # to adjust all the tests.  Note that the returned AST is NOT
    # multiplexed.
    def __iter__(self):
        self.assertHasVariants()
        return iter((self.variants[0].build.syntax_tree, self))

    def add_variant(self, *args):
        for backend in self.backends:
            variant = backend(self.env, *args)
            if variant.is_testable:
                self.variants.append(variant)

def multiplexed(func):
    """Run a TestCase method once per each output variant.

    Some tests cannot be run against a multiplexed TestOutput, for
    example tests for side effects such as printing.  This decorator
    is used to cause a TestCase method to be invoked once per output
    variant.

    Modifies TestCase.output if set; modifies args[0] otherwise.
    Sets TestCase.variant_index as it progresses.
    """
    def wrapper(self, *args, **kwargs):
        mux = getattr(self, "output", None)
        using_self_output = mux is not None
        if not using_self_output:
            args = list(args)
            mux = args[0]
        try:
            for self.variant_index, variant in enumerate(mux.variants):
                try:
                    if using_self_output:
                        self.output = variant
                    else:
                        args[0] = variant
                    with self._install_context(variant):
                        func(self, *args, **kwargs)
                finally:
                    del self.variant_index
        finally:
            if using_self_output:
                self.output = mux

    wrapper.__name__ = func.__name__
    return wrapper

class TestCase(BaseTestCase):
    __i8c_testcase__ = True

    topdir = os.path.realpath(__file__)
    topdir, check = os.path.split(topdir)
    assert check.startswith("__init__.py")
    topdir, module = os.path.split(topdir)
    assert os.path.exists(os.path.join(topdir, "setup.py"))
    del check

    outdir = os.path.join(topdir, module, "output")
    subprocess.check_call(("rm", "-rf", outdir))
    outdir = os.path.basename(outdir)

    assemblers = AssemblerManager()

    print("using Python", sys.version.split("\n", 1)[0], file=sys.stderr)
    TestOutput.announce()
    assemblers.announce()

    system_byteorder = {"little": b"<", "big": b">"}[sys.byteorder]

    __compilecounts = {}

    def run(self, *args, **kwargs):
        for logger in compiler.loggers.values():
            logger.disable()
        try:
            return BaseTestCase.run(self, *args, **kwargs)
        finally:
            self._ctx = None

    @property
    def memory(self):
        return self._ctx.memory

    def _new_compilation(self):
        """Update compilation count and return a new TestOutput.
        """
        self.assertEqual(os.getcwd(), self.topdir)
        tmp = self.id().split(".")
        self.assertEqual(tmp[0], self.module)
        self.assertTrue(tmp.pop(-2).startswith("Test"))
        tmp.insert(1, self.outdir)
        fileprefix = os.path.join(*tmp)

        index = self.__compilecounts.get(fileprefix, 0) + 1
        self.__compilecounts[fileprefix] = index
        fileprefix += "_%04d" % index

        result = TestOutput(self, fileprefix)
        self._ctx = result
        return result

    def compile(self, input, **kwargs):
        """Compile I8Language to object code, then load resulting notes.

        Returns a tuple, the first element of which is the syntax tree
        after I8C has run, and the second element of which is a context
        with all notes from the generated object code loaded.
        """
        return TestCompiler(self).compile(input, **kwargs)

    def i8compile(self, input, **kwargs):
        """Compile preprocessed I8Language to assembly language.

        Returns a tuple, the first element of which is the AST after
        I8C has run, and the second element of which is the generated
        assemble language.
        """
        input = io.BytesIO(input.encode("utf-8"))
        output = io.BytesIO()
        tree = compiler.compile(input.readline, output.write, **kwargs)
        return tree, output.getvalue().decode("utf-8")

    def load_precompiled(self):
        """Load a precompiled input file.

        This is for testing failures that can't easily be replicated,
        for example because a specific compiler is required.  Note
        that the input directory is not shipped in the tarball to
        avoid licensing issues, so these tests automatically skip if
        their input file is not found.
        """
        result = self._new_compilation()

        tmp = result.fileprefix.split(os.sep)
        self.assertEqual(len(tmp), 4)
        self.assertEqual(tmp[0], self.module)
        self.assertEqual(tmp[1], self.outdir)
        tmp[1] = "precompiled"

        pattern = os.path.join(*tmp[:-1]) + "*"
        matches = glob.glob(pattern)
        if not matches:
            self.skipTest(pattern + " not found")
        self.assertEqual(len(matches), 1)
        filename = matches[0]

        build = CompilerTask(result.fileprefix)
        build.asm_output_file = filename
        result.add_variant(build)

        return result

# -*- coding: utf-8 -*-
# Copyright (C) 2017 Red Hat, Inc.
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

from tests import TestCase, TestCompiler, multiplexed
from i8c import constants
from i8c.compiler import commands
from i8c.runtime import SymbolError
import os
import sys

MAIN_SYMBOL = "a_symbol"
ALIAS_SYMBOL = "__GI_" + MAIN_SYMBOL

SOURCE = """\
define test::relocation_test returns ptr
    extern ptr %s
    load %s
""" % (MAIN_SYMBOL, MAIN_SYMBOL)

BASIC_SYMDEF = 'const char *%s = "Hello World";' % MAIN_SYMBOL

LOCAL_SYMDEF = """\
static %s

const char *
a_function (void)
{
  return %s;
}
""" % (BASIC_SYMDEF, MAIN_SYMBOL)

ALIAS_SYMDEF = """\
// glibc/src/include/list.h

typedef struct list_head
{
  struct list_head *next;
  struct list_head *prev;
} list_t;

// glibc/src/include/libc-symbols.h

#  define __hidden_proto_hiddenattr(attrs...) \
  __attribute__ ((visibility ("hidden"), ##attrs))
#  define hidden_proto(name, attrs...) \
  __hidden_proto (name, , __GI_##name, ##attrs)
#  define hidden_tls_proto(name, attrs...) \
  __hidden_proto (name, __thread, __GI_##name, ##attrs)
#  define __hidden_proto(name, thread, internal, attrs...)	     \
  extern thread __typeof (name) name __asm__ (__hidden_asmname (#internal)) \
  __hidden_proto_hiddenattr (attrs);
#  define __hidden_asmname(name) \
  __hidden_asmname1 (__USER_LABEL_PREFIX__, name)
#  define __hidden_asmname1(prefix, name) __hidden_asmname2(prefix, name)
#  define __hidden_asmname2(prefix, name) #prefix name
#  define __hidden_ver1(local, internal, name) \
  extern __typeof (name) __EI_##name __asm__(__hidden_asmname (#internal)); \
  extern __typeof (name) __EI_##name \
	__attribute__((alias (__hidden_asmname (#local))))
#  define hidden_ver(local, name)	__hidden_ver1(local, __GI_##name, name);
#  define hidden_data_ver(local, name)	hidden_ver(local, name)
#  define hidden_def(name)		__hidden_ver1(__GI_##name, name, name);
#  define hidden_data_def(name)		hidden_def(name)
#  define hidden_weak(name) \
	__hidden_ver1(__GI_##name, name, name) __attribute__((weak));
#  define hidden_data_weak(name)	hidden_weak(name)
#  define hidden_nolink(name, lib, version) \
  __hidden_nolink1 (__GI_##name, __EI_##name, name, VERSION_##lib##_##version)
#  define __hidden_nolink1(local, internal, name, version) \
  __hidden_nolink2 (local, internal, name, version)
#  define __hidden_nolink2(local, internal, name, version) \
  extern __typeof (name) internal __attribute__ ((alias (#local))); \
  __hidden_nolink3 (local, internal, #name "@" #version)
#  define __hidden_nolink3(local, internal, vername) \
  __asm__ (".symver " #internal ", " vername);

// glibc/src/nptl/pthreadP.h

extern list_t __stack_user;
hidden_proto (__stack_user)

// glibc/src/nptl/allocatestack.c

list_t __stack_user __attribute__ ((nocommon));
hidden_data_def (__stack_user)
""".replace("__stack_user", MAIN_SYMBOL)

MAIN_C = r"""\
extern const char *%s;

int
main ()
{
  return !%s;
}
""" % (MAIN_SYMBOL, MAIN_SYMBOL)

class SymInNoteObjfile(object):
    I8C_KWARGS = {"wrap_asm": True}

    def postprocess(self, build, output):
        return output + "\n" + self.SYMDEF

class SymInOwnObjfile(object):
    def setup_build(self, build):
        filename = build.writable_filename("-symbol.c")
        build.write_file(self.SYMDEF, filename)
        build.add_sourcefile(filename)

class LinkSolib(object):
    def link(self, build, assembler, objfiles):
        filename = build.writable_filename(".so")
        assembler.check_call(["-shared"] + objfiles + ["-o", filename],
                             fail_softly=True)
        return filename

class StaticLinker(commands.CompilerCommand):
    """Program for creating static libraries.
    """
    DEFAULT = commands._getenv("I8CTEST_AR", ["ar"])

class LinkStatic(object):
    def link(self, build, assembler, objfiles):
        filename = build.writable_filename(".a")
        StaticLinker().check_call(["rcs", filename] + objfiles)
        return filename

class LinkExe(LinkStatic):
    def setup_build(self, build):
        self.__main_c = build.writable_filename("-main.c")
        build.write_file(self.MAIN_C, self.__main_c)

    def link(self, build, assembler, objfiles):
        library = LinkStatic.link(self, build, assembler, objfiles)
        filename = build.writable_filename("")
        assembler.check_call([self.__main_c, library, "-o", filename],
                             fail_softly=True)
        return filename

class StripResult(object):
    def postlink(self, build, assembler, linked):
        strip = commands._getenv("I8CTEST_STRIP", None)
        if strip is None:
            strip = ["-".join(assembler.args[0].split("-")[:-1] + ["strip"])]
        strip = commands.CompilerCommand(strip)
        strip.check_call([linked])
        return linked

class TestRelocation(TestCase):
    def test_relocation(self):
        """Test relocation."""
        for symdef in (None, BASIC_SYMDEF, ALIAS_SYMDEF, LOCAL_SYMDEF):
            # None: the symbol is undefined.
            # Basic: the symbol is defined.
            # Alias: the symbol is defined, with an alias.
            # Local: the symbol is defined static.

            if symdef is None:
                symlocs = (None,)
            else:
                symlocs = (SymInNoteObjfile, SymInOwnObjfile)

            for symloc in symlocs:
                # None: the symbol is undefined.
                # InNoteObjfile: the symbol is defined in the same
                #   object file as the note that references it.
                # InOwnObjfile: the symbol and referencing note are
                #   defined in separate object files.

                for linker in (None, LinkSolib, LinkStatic, LinkExe):
                    # None: I8X is testing .o
                    # Solib: I8X is testing .so
                    # Static: I8X is testing .a
                    # Exe: I8X is testing a static exe

                    for post in (None, StripResult):
                        # None: Linker output is not stripped
                        # StripResult: Linker output is stripped

                        self.__test_relocation(symdef, symloc, linker, post)

    def __test_relocation(self, symdef, symloc, linker, post):
        # Should have a definition and a location, or neither.
        self.assertEqual(symdef is None, symloc is None)

        # This combination doesn't make sense, and will fail
        # an assertion in TestCompiler.link.
        if linker is None and symloc is SymInOwnObjfile:
            return

        # GCC's linker includes code on a per-object-file basis when
        # linking statically.  This means the Infinity notes will be
        # omitted unless they're in a file with something else that's
        # going to cause them to be pulled in.
        if linker is LinkExe and symloc is not SymInNoteObjfile:
            return

        compiler = self.__make_compiler(symdef, symloc, linker, post)
        tree, output = compiler.compile(SOURCE)

        # Most stripped inputs result in SymbolErrors.
        if (post is StripResult
            and (linker is not LinkSolib
                 or (symdef is LOCAL_SYMDEF
                     and symloc is SymInNoteObjfile))):
            self.assertImportRaised(output, SymbolError)
            return

        # Check the decoded bytecode looks right.
        expect_symbols = [MAIN_SYMBOL]
        if (symdef is ALIAS_SYMDEF
              and linker in (LinkSolib, LinkExe)
              and post is not StripResult):
            expect_symbols.append(ALIAS_SYMBOL)
        self.assertEqual(output.opnames, ["addr"])
        actual_symbols = output.ops[0].operand
        self.assertEqual(sorted(expect_symbols), sorted(actual_symbols))

        # Call the function with all combinations of the two
        # symbols being registered or not.
        for register_main in ([], [MAIN_SYMBOL]):
            for register_alias in ([], [ALIAS_SYMBOL]):
                register_symbols = register_main + register_alias
                self.__check_call_testfunc(output,
                                           register_symbols,
                                           actual_symbols)

    @multiplexed
    def __check_call_testfunc(self, output, register_symbols,
                              lookup_symbols):
        output._i8ctest_reset_symbols()
        if register_symbols:
            expect_result = id(self) & ((1 << output.wordsize) - 1)
            for symbol in register_symbols:
                output.register_symbol(symbol, expect_result)
            expect_result = [expect_result]

        for symbol in lookup_symbols:
            if symbol in register_symbols:
                # It should work.
                self.assertEqual(output.call(output.note.signature),
                                 expect_result)
                return

        # It should fail.
        with self.assertRaises(SymbolError) as cm:
            output.call(output.note.signature)
        self.__check_symbolerror(cm.exception, lookup_symbols)

    def __make_compiler(self, symdef, addsym_mixin, linker_mixin, strip_mixin):
        name = ["RelocTestCompiler"]
        bases = [TestCompiler]
        _dict = {}

        if symdef is None:
            self.assertIsNone(addsym_mixin)
            name.append("NoSym")
        else:
            self.assertIsNotNone(addsym_mixin)
            cname = self.__classname(addsym_mixin)
            name.append({BASIC_SYMDEF: "Basic",
                         LOCAL_SYMDEF: "Local",
                         ALIAS_SYMDEF: "Alias"}[symdef] + cname[:3])
            name.append(cname[3:])
            bases.append(addsym_mixin)
            _dict["SYMDEF"] = symdef

        if linker_mixin is None:
            name.append("Unlinked")
        else:
            cname = self.__classname(linker_mixin)
            name.append(cname[4:] + cname[:4])
            bases.append(linker_mixin)

        if linker_mixin is LinkExe:
            main_c = MAIN_C
            if symdef is LOCAL_SYMDEF:
                main_c = main_c.replace(MAIN_SYMBOL, "a_function ()")
            _dict["MAIN_C"] = main_c

        if strip_mixin is not None:
            name.append("Stripped")
            bases.append(strip_mixin)

        print("Testing", ", ".join(name[1:]))

        name = "_".join(name)
        if sys.version_info < (3,):
            name = name.encode("utf-8")
        return type(name, tuple(reversed(bases)), _dict)(self)

    def __classname(self, cls):
        return eval(str(cls).rstrip(">").split()[1]).split(".")[-1]

    @multiplexed
    def assertImportRaised(self, output, exc_cls):
        self.assertTrue(isinstance(output.import_error, exc_cls))
        self.__check_symbolerror(output.import_error)

    def __check_symbolerror(self, exc, expect_names=None):
        location, msg = exc.args[0].split("]: error: ", 1)
        self.__check_symbolerror_msg(msg, expect_names)
        filename, offset = self.__parse_symbolerror_location(location)
        self.assertGreater(offset, 0)
        with open(filename, "rb") as fp:
            fp.seek(offset - 1)
            opcode = fp.read(1)
            if sys.version_info >= (3,):
                [opcode] = opcode
            else:
                opcode = ord(opcode)
        self.assertEqual(opcode, constants.DW_OP_addr)

    def __check_symbolerror_msg(self, msg, expect_names):
        if expect_names is None:
            self.assertEqual(msg, "no matching symbols found")
            return

        prefix = "unresolved symbol "
        self.assertTrue(msg.startswith(prefix))
        expect_names = ["‘%s’" % name for name in expect_names]
        actual_names = msg[len(prefix):].split(", ")
        self.assertEqual(expect_names, actual_names)

    def __parse_symbolerror_location(self, location):
        location = location.split("[")
        offset = int(location.pop(), 16)
        filename = location.pop(0)
        if location:
            self.assertTrue(filename.endswith(".a"))
            [objfile] = location
            self.assertTrue(objfile.endswith(".o]"))
            filename = os.path.join(os.path.dirname(filename),
                                    objfile[:-1])
        return filename, offset

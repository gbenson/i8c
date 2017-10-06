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
        assembler.check_call(["-shared"] + objfiles + ["-o", filename])
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
        build.write_file(MAIN_C, self.__main_c)

    def link(self, build, assembler, objfiles):
        library = LinkStatic.link(self, build, assembler, objfiles)
        filename = build.writable_filename("")
        assembler.check_call([self.__main_c, library, "-o", filename])
        return filename

class TestRelocation(TestCase):
    def test_relocation(self):
        """Test relocation."""
        for symdef in (None, BASIC_SYMDEF, ALIAS_SYMDEF):
            # None: the symbol is undefined.
            # Basic: the symbol is defined.
            # Alias: the symbol is defined, with an alias.

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

                    self.__test_relocation(symdef, symloc, linker)

    def __test_relocation(self, symdef, symloc, linker):
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

        compiler = self.__make_compiler(symdef, symloc, linker)
        tree, output = compiler.compile(SOURCE)

        # Solib with undefined symbol results in SymbolError.
        if linker is LinkSolib and symdef is None:
            self.assertImportRaised(output, SymbolError)
            return

        # Running with no symbol registered should fail.
        self.__check_call_testfunc(output, None, False)

        # Running with the alias symbol registered should
        # succeed only for cases with it defined.
        self.__check_call_testfunc(output, ALIAS_SYMBOL,
                                   symdef is ALIAS_SYMDEF
                                   and linker in (LinkSolib, LinkExe))

        # Running with the symbol registered should succeed.
        self.__check_call_testfunc(output, MAIN_SYMBOL, True)

    @multiplexed
    def __check_call_testfunc(self, output, symname, expect_success):
        print(" ", output.build.asm_output_file, repr(symname).lstrip("u"))
        output._i8ctest_reset_symbols()
        if symname is not None:
            expect_result = id(self) & ((1 << output.wordsize) - 1)
            output.register_symbol(symname, expect_result)
            expect_result = [expect_result]
        if expect_success:
            self.assertEqual(output.call(output.note.signature),
                             expect_result)
        else:
            with self.assertRaises(KeyError) as cm:
                output.call(output.note.signature)
            self.assertIn(cm.exception.args[0], (MAIN_SYMBOL,
                                                 ALIAS_SYMBOL))

    def __make_compiler(self, symdef, addsym_mixin, linker_mixin):
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

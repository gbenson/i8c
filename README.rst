GNU Infinity Note Compiler
==========================

GNU Infinity is a platform-independent system for executables and
shared libraries to export information to software development tools
such as debuggers.

In GNU Infinity, executable and shared library files contain *infinity
notes* in addition to their regular contents.  Each infinity note
contains a function encoded in a platform-independent instruction
set that note-consuming tools can load and execute.

This package provides I8C, a compiler for creating object files
containing infinity notes.  This package also provides I8X, an
execution environment that can be used to create unit tests for
compiled notes.


Installation
------------

The easiest way to install this software is to use pip::

  sudo pip install -U i8c

The latest development version is available from GitHub_.


Note Compiler
-------------

The note compiler’s standard mode of operation is to translate I8
source code into object files which can be linked into executables
or shared libraries in the usual manner.  This example will
generate the file |factorial.o|::

  cd examples/factorial
  i8c -c factorial.i8

I8C uses GCC both to preprocess its input (unless invoked with
|-fpreprocessed|) and to assemble its output (unless invoked with
|-E| or |-S|).  If GCC is used, all options not explicitly listed
by |i8c --help| will be passed to GCC unmodified.  In general I8C
operates like GCC, so if you’re used to using GCC then I8C should
make sense.


Execution Environment
---------------------

I8X is an execution environment for testing GNU Infinity notes.  When
invoked as |i8x --quick| (or |i8x -q|) I8X executes a single note
function, taking arguments from the command line and displaying the
result on the console::

  cd examples/factorial
  i8x -i factorial.o -q "example::factorial(i)i" 5

When invoked without |-q| or |--quick| I8X expects one or more note
testcases to be specified on the command line.  Note testcases are
written in Python using an extension of the unittest_ unit testing
framework.  Testcases execute note functions with specific inputs and
check the operation and result of the call proceeds as expected.  This
example tests the |factorial.o| object file created in the first
example above::

  cd examples/factorial
  i8x -i factorial.o test-factorial.py


Documentation
-------------

Right now there is no documentation apart from this file (sorry!)


Contributing
------------

To report a bug please use the `issue tracker`_.

If you’re working on this software please note what you’re doing in
the issue tracker or email gbenson@redhat.com so we don’t collide.


.. reStructuredText stuff:

.. Links
.. _GitHub: https://github.com/gbenson/i8c/
.. _issue tracker: https://github.com/gbenson/i8c/issues/
.. _unittest: https://docs.python.org/2/library/unittest.html

.. Substitutions
.. |factorial.o| replace:: :code:`factorial.o`
.. |-fpreprocessed| replace:: :code:`-fpreprocessed`
.. |-E| replace:: :code:`-E`
.. |-S| replace:: :code:`-S`
.. |i8c --help| replace:: :code:`i8c --help`
.. |i8x -q| replace:: :code:`i8x -q`
.. |i8x --quick| replace:: :code:`i8x --quick`
.. |-q| replace:: :code:`-q`
.. |--quick| replace:: :code:`--quick`

What has changed in I8C?
========================

Changes since I8C 0.0.1
-----------------------

Bug fixes
~~~~~~~~~

* Older versions of unittest are detected and handled in setup.py;
  both the testsuite and I8X should now work out of the box with
  Python 2.6 and 3.1.

* "i8c -S" now outputs to a file unless "-o -" is specified on the
  command line.  (https://github.com/gbenson/i8c/issues/32)

* Stack underflow checks in I8C were off by one in some cases.

* I8C's parser now correctly raises an error if arguments are supplied
  for zero-argument operations.

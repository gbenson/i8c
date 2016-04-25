# -*- coding: utf-8 -*-
# Copyright (C) 2016 Red Hat, Inc.
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

# Export notes built by the testsuite for libi8x's corpus.

import hashlib
import os
import subprocess
import sys

topdir = os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0])))
outdir = os.path.join(topdir, "tests", "output")
subprocess.check_call(("/bin/rm", "-rf", outdir))
env = os.environ.copy()
env.update({"LIBI8X_TESTNOTE_EXPORT": "1"})
subprocess.check_call((sys.executable, "setup.py", "test"), env=env)
outdir = os.path.join(outdir, "for-libi8x")

filenames = []
for dirname, dirs, files in os.walk(outdir):
    for filename in files:
        filenames.append(os.path.join(dirname, filename))

# Don't bundle multiple copies of the same bytes.
by_md5sum = {}
strip = len(outdir + os.sep)
for filename in sorted(filenames):
    hash = hashlib.md5()
    with open(filename, "rb") as fp:
        block = fp.read(4096)
        if not block:
            break
        hash.update(block)
    md5sum = hash.hexdigest()
    if md5sum not in by_md5sum:
        by_md5sum[md5sum] = filename[strip:]

outfile = os.path.join(topdir, "notes-for-libi8x.tar")
subprocess.check_call(("/bin/tar", "-cf", outfile, "-C", outdir)
                      + tuple(by_md5sum.values()))

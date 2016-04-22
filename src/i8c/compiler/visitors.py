# -*- coding: utf-8 -*-
# Copyright (C) 2015-16 Red Hat, Inc.
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

class VisitError(NotImplementedError):
    def __init__(self, visitor, visitee):
        NotImplementedError.__init__(
            self,
            "%s has no visitor suitable for %s" % (
                    visitor.__class__.__name__,
                    visitee.__class__.__name__))

class Visitable(object):
    @classmethod
    def get_visitfunc(cls, visitor):
        func = getattr(visitor, "visit_" + cls.__name__.lower(), None)
        if func is None:
            for cls in cls.__bases__:
                if cls is not Visitable and issubclass(cls, Visitable):
                    func = cls.get_visitfunc(visitor)
                    if func is not None:
                        break
        return func

    def accept(self, visitor):
        # Find a suitable visitor
        func = self.get_visitfunc(visitor)
        if func is None:
            raise VisitError(visitor, self)
        # Visit any folded children first
        if hasattr(self, "folded_children"):
            for node in self.folded_children:
                node.accept(visitor)
        # Now visit ourself
        return func(self)

# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals


class Walker(object):
    def _walk(self, tree):
        if isinstance(tree, tuple):
            return self._handle_operator(tree[0], [self._walk(argument) for argument in tree[1:]])
        else:
            return self._handle_argument(tree)

    def _handle_operator(self, operator, arguments):
        raise NotImplementedError

    def _handle_argument(self, argument):
        raise NotImplementedError

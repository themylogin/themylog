# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from themylog.rules_tree.walker import Walker


class Evaluator(Walker):
    def __init__(self, get_record_key, constant_map=None, operator_map=None):
        self.get_record_key = get_record_key
        self.constant_map = constant_map or {}
        self.operator_map = operator_map or {}
        super(Evaluator, self).__init__()

    def eval(self, tree):
        return self._walk(tree)

    def _handle_operator(self, operator, arguments):
        if operator in self.operator_map:
            operator = self.operator_map[operator]

        return operator(*arguments)

    def _handle_argument(self, arg):
        if arg in self.constant_map:
            return self.constant_map[arg]

        if callable(arg):
            return arg(self.get_record_key)

        return arg

# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import themylog.rules_tree
from themylog.rules_tree.walker import Walker


class ParameterSubstituter(Walker):
    def __init__(self, parameters):
        self.parameters = parameters
        super(ParameterSubstituter, self).__init__()

    def substitute(self, tree):
        return self._walk(tree)

    def _handle_operator(self, operator, arguments):
        return (operator,) + tuple(arguments)

    def _handle_argument(self, argument):
        if isinstance(argument, themylog.rules_tree.Param):
            return self.parameters[argument.name]

        return argument

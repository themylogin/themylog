# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from themylog.rules_tree.evaluator import Evaluator
from themylog.rules_tree.parameter_substituter import ParameterSubstituter


class Param(object):
    def __init__(self, name):
        self.name = name


class RecordField(object):
    def __init__(self, field):
        self.field = field

    def __call__(self, get_record_key):
        return get_record_key(self.field)


def match_record(tree, record):
    return Evaluator(lambda key: getattr(record, key)).eval(tree)


def substitute_parameters(tree, values):
    return ParameterSubstituter(values).substitute(tree)

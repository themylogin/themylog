from __future__ import absolute_import

from themylog.rules_tree.evaluator import Evaluator


def match_record(tree, record):
    return Evaluator(lambda key: getattr(record, key)).eval(tree)

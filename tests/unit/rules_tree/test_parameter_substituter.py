# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import operator
import unittest

from themylog.rules_tree import Param as P
from themylog.rules_tree.parameter_substituter import ParameterSubstituter


class ParameterSubstituterTestCase(unittest.TestCase):
    def test_substitution(self):
        self.assertEqual(ParameterSubstituter({"a": 1, "b": 3}).substitute((operator.and_, (operator.eq, 0, P("a")),
                                                                                           (operator.eq, 2, P("b")))),
                         (operator.and_, (operator.eq, 0, 1),
                                         (operator.eq, 2, 3)))

# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import ast
import unittest

from themylog.annotations import NoneValue
from themylog.annotations.timeout import timeout


class TimeoutTestCase(unittest.TestCase):
    def test_timeout(self):
        self.assertEqual(timeout(ast.parse("timeout = 300")), 300)
        self.assertEqual(timeout(ast.parse("timeout = None")), NoneValue)

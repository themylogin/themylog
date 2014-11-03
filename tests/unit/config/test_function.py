# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import unittest

from themylog.config.function import get_function


class ConfigGetFunctionTestCase(unittest.TestCase):
    def test_it_works(self):
        f = get_function("arg1", "if arg1 is None:\n    return 666\nelse:    return arg1")
        self.assertEqual(f(None), 666)
        self.assertEqual(f(15), 15)

# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import ast
import unittest

from themylog.annotations.title import title


class TitleTestCase(unittest.TestCase):
    def test_title(self):
        self.assertEqual(title(ast.parse("title = 'Юникод'")), "Юникод")

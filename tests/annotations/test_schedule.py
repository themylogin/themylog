# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import ast
from mock import Mock
from testfixtures import replace
import unittest

from themylog.annotations.schedule import schedule


class CreateScheduleTestCase(unittest.TestCase):
    @replace("themylog.annotations.schedule.crontab", Mock())
    def test_creates_schedule(self, crontab):
        schedule(ast.parse("crontab(hour=7, minute='*/15')"))
        crontab.assert_called_once_with(hour=7, minute='*/15')

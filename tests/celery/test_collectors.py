# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import ast
from mock import MagicMock, Mock
from testfixtures import replace, Replacer
import textwrap
import unittest

from themylog.celery.collectors import read_annotations, create_schedule


class ReadAnnotationsTestCase(unittest.TestCase):
    def create_fake_ast_parse(self, *acceptable_code):
        def fake_ast_parse(code):
            if code in acceptable_code:
                return code
            else:
                raise SyntaxError

        return fake_ast_parse

    def test_all_annotations(self):
        with Replacer() as r:
            ast = Mock(parse=self.create_fake_ast_parse("1 > 0"))
            r.replace("themylog.celery.collectors.ast", ast)

            create_schedule = Mock()
            r.replace("themylog.celery.collectors.create_schedule", create_schedule)

            read_annotations(textwrap.dedent("""
                # -*- coding: utf-8 -*-
                # This is my script, called when
                # 1 > 0
                # All rights reserved
            """).strip())

            create_schedule.assert_called_once_with("1 > 0")


class CreateScheduleTestCase(unittest.TestCase):
    @replace("themylog.celery.collectors.crontab", Mock())
    def test_creates_schedule(self, crontab):
        create_schedule(ast.parse("crontab(hour=7, minute='*/15')"))
        crontab.assert_called_once_with(hour=7, minute='*/15')

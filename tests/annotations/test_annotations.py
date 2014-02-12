# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from mock import Mock
from testfixtures import Replacer
import textwrap
import unittest

from themylog.annotations import read_annotations


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
            r.replace("themylog.annotations.ast", ast)

            annotation_parser = Mock()
            annotation_parsers = {"annotation": annotation_parser}

            read_annotations(textwrap.dedent("""
                # -*- coding: utf-8 -*-
                # This is my script, called when
                # 1 > 0
                # All rights reserved
            """).strip(), annotation_parsers)

            annotation_parser.assert_called_once_with("1 > 0")

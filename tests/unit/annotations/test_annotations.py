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

    def test_annotations_are_being_parsed(self):
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

    def test_annotations_are_being_stored(self):
        with Replacer() as r:
            code1 = "1 > 0"
            code2 = "2 + 2 = 4"

            ast = Mock(parse=self.create_fake_ast_parse(code1, code2))
            r.replace("themylog.annotations.ast", ast)

            parser1 = lambda ast: "result1" if ast == code1 else None
            parser2 = lambda ast: "result2" if ast == code2 else None
            annotation_parsers = {"annotation1": parser1, "annotation2": parser2}

            annotations = read_annotations(textwrap.dedent("""
                # -*- coding: utf-8 -*-
                # This is my script, called when
                # 1 > 0
                # 2 + 2 = 4
            """).strip(), annotation_parsers)

            self.assertEqual(annotations, {"annotation1": "result1", "annotation2": "result2"})


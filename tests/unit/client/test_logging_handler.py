# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
from mock import Mock
from testfixtures import replace
import unittest

from themylog.client import LoggingHandler


def instantiates_client(test):
    test = replace("themylog.client.find_config", Mock())(test)
    test = replace("themylog.client.read_config", Mock(return_value={"receivers": [],
                                                                     "handlers": []}))
    return test


class GetLevelTestCase(unittest.TestCase):
    def create_fake_record(self, **kwargs):
        record_kwargs = dict(name="root",
                             level=logging.NOTSET,
                             pathname="/fake.py",
                             lineno=1,
                             msg="",
                             args=(),
                             exc_info=None,
                             func="fake")

        record_kwargs.update(kwargs)

        return logging.LogRecord(**record_kwargs)

    @instantiates_client
    def test_ordinary_record(self):
        h = LoggingHandler(None)
        r = self.create_fake_record(level=logging.WARNING)
        self.assertEqual(h._get_level(r), "warning")

    @instantiates_client
    def test_exception_record(self):
        h = LoggingHandler(None, exception_level="error")
        r = self.create_fake_record(level=logging.WARNING, exc_info=(Exception,))
        self.assertEqual(h._get_level(r), "error")


class UnderscoreMessageTestCase(unittest.TestCase):
    @instantiates_client
    def setUp(self):
        self.h = LoggingHandler(None)

    def test_underscoring_works(self):
        self.assertEqual(self.h._underscore_message("Inserted %d scrobbles for %s"), "inserted_d_scrobbles_for_s")

    def test_trailing_underscore_strip(self):
        self.assertEqual(self.h._underscore_message("update_scrobbles('%s', asap=%r)"), "update_scrobbles_s_asap_r")

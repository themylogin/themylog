# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from mock import Mock
import unittest


class DisorderSeekerAbstractTestCase(unittest.TestCase):
    def setUp(self):
        self.observer = Mock()

    def fake_record(self, **kwargs):
        record = Mock()
        for k, v in kwargs.items():
            setattr(record, k, v)
        return record

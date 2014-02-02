# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
import unittest

import themylog.json


class LoadsTestCase(unittest.TestCase):
    def test_datetime(self):
        self.assertEqual(themylog.json.loads('{"data": {"datetime": "2014-02-02T17:32:01", "datetimes": [{"asdict": '+\
                                             '"2014-02-02T17:32:02"}, "2014-02-02T17:32:03"]}}'),
                         {"data": {"datetime": datetime(2014, 02, 02, 17, 32, 01),
                                   "datetimes": [{"asdict": datetime(2014, 02, 02, 17, 32, 02)},
                                                 datetime(2014, 02, 02, 17, 32, 03)]}})


class DumpsTestCase(unittest.TestCase):
    def test_datetime(self):
        self.assertEqual(themylog.json.dumps({"datetime": datetime(2014, 02, 02, 17, 32, 01)}),
                         '{"datetime": "2014-02-02T17:32:01"}')

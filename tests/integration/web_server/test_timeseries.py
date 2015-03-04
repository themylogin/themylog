# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
import time

from themylog.level import levels
from themylog.record import Record

from . import WebserverTestCase


class TimeseriesTestCase(WebserverTestCase):
    def test_http_expiration(self):
        self.start(self.config)

        self.log_and_wait(Record(application="theMediaShell",
                                 logger="movie",
                                 datetime=datetime.now(),
                                 level=levels["info"],
                                 msg="progress",
                                 args={"movie": "Life.Cycles.mkv"},
                                 explanation=""))
        self.assertRequest("/timeseries/theMediaShell", {"movie": "Life.Cycles.mkv"})

        self.assertRequest("/timeseries/theMediaShell?timeout=2", {"movie": "Life.Cycles.mkv"})
        time.sleep(2)
        self.assertRequest("/timeseries/theMediaShell?timeout=2", None)
        self.assertRequest("/timeseries/theMediaShell?timeout=5", {"movie": "Life.Cycles.mkv"})

    def test_websocket_expiration(self):
        self.start(self.config)

        self.log_and_wait(Record(application="theMediaShell",
                                 logger="movie",
                                 datetime=datetime.now(),
                                 level=levels["info"],
                                 msg="progress",
                                 args={"movie": "Life.Cycles.mkv"},
                                 explanation=""))
        reader = self.websocketReader("/timeseries/theMediaShell?timeout=2")

        time.sleep(0.5)
        self.assertEqual(len(reader), 1)
        self.assertEqual(reader[-1], {"movie": "Life.Cycles.mkv"})

        time.sleep(3)
        self.assertEqual(len(reader), 2)
        self.assertEqual(reader[-1], None)

    def test_websocket_first_receives_null_if_nothing_available_within_timeout(self):
        self.start(self.config)

        reader = self.websocketReader("/timeseries/theMediaShell?timeout=2")

        time.sleep(0.5)
        self.assertEqual(len(reader), 1)
        self.assertEqual(reader[-1], None)

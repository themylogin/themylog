# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
import time

from themylog.level import levels
from themylog.record import Record

from . import WebserverTestCase

class TimelineTestCase(WebserverTestCase):
    def test_websocket_old_incoming_records_do_not_overlap_new_ones(self):
        self.start(self.config)

        self.log_and_wait(Record(application="alfa-bank",
                                 logger="root",
                                 datetime=datetime(2015, 04, 15, 10, 56, 02),
                                 level=levels["info"],
                                 msg="Ostatok: 100,37 RUR",
                                 args={"balance": 100.37},
                                 explanation=""))

        reader = self.websocketReader("/timeline/alfa-bank")

        time.sleep(0.5)
        self.assertEqual(len(reader), 1)
        self.assertEqual(reader[-1], {"balance": 100.37})

        self.log_and_wait(Record(application="alfa-bank",
                                 logger="root",
                                 datetime=datetime(2015, 04, 17, 14, 23, 20),
                                 level=levels["info"],
                                 msg="Ostatok: 65,77 RUR",
                                 args={"balance": 65.77},
                                 explanation=""))

        time.sleep(0.5)
        self.assertEqual(len(reader), 2)
        self.assertEqual(reader[-1], {"balance": 65.77})

        self.log_and_wait(Record(application="alfa-bank",
                                 logger="root",
                                 datetime=datetime(2015, 04, 11, 14, 46, 23),
                                 level=levels["info"],
                                 msg="Ostatok: 4360,99 RUR",
                                 args={"balance": 4360.99},
                                 explanation=""))

        time.sleep(0.5)
        self.assertEqual(len(reader), 2)
        self.assertEqual(reader[-1], {"balance": 65.77})

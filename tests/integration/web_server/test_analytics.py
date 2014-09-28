# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime, timedelta
import textwrap
import time

from themylog.level import levels
from themylog.record import Record

from . import WebserverTestCase


class AnalyticsTestCase(WebserverTestCase):
    awake = textwrap.dedent("""
        # -*- coding: utf-8 -*-
        from __future__ import absolute_import, division, unicode_literals

        from datetime import datetime
        import operator

        from themylog.rules_tree import Param as P, RecordField as F

        feeds = {"last_sleep_track": {"rules_tree": (operator.and_, (operator.eq, F("logger"), "sleep_tracker"),
                                                                    (operator.or_, (operator.eq, F("msg"), "woke_up"),
                                                                                   (operator.eq, F("msg"), "fall_asleep"))),
                                      "limit": 1},
                 "odometer_logs": {"rules_tree": (operator.and_, (operator.eq, F("application"), "usage_stats"),
                                                                 (operator.gt, F("datetime"), P("last_sleep_track_datetime"))),
                                   "params": {"last_sleep_track_datetime": lambda last_sleep_track: last_sleep_track.args["at"]
                                                                                                    if last_sleep_track.msg == "woke_up"
                                                                                                    else datetime.max}}}


        def analyze(last_sleep_track, odometer_logs):
            now = datetime.now()

            if last_sleep_track.msg == "woke_up":
                woke_up_at = last_sleep_track.args["at"]
                seconds_up = (now - woke_up_at).total_seconds()

                seconds_pc = 0
                for prev_log, log in zip(odometer_logs, [None] + odometer_logs)[1:]:
                    if log.args["keys"] > 0 or log.args["pixels"] > 0:
                        seconds_pc += (log.datetime - prev_log.datetime).total_seconds()

                return {"state": "up",
                        "seconds_up": seconds_up,
                        "seconds_pc": seconds_pc}
            else:
                return {"state": "down"}
    """).strip()

    def init_awake(self):
        self.log_and_wait(Record(application="usage_stats",
                                 logger="desktop",
                                 datetime=datetime.now() - timedelta(hours=5),
                                 level=levels["info"],
                                 msg="data",
                                 args={"keys": 3, "pixels": 1920},
                                 explanation=""))
        self.log_and_wait(Record(application="smarthome",
                                 logger="sleep_tracker",
                                 datetime=datetime.now() - timedelta(minutes=5),
                                 level=levels["info"],
                                 msg="woke_up",
                                 args={"at": datetime.now() - timedelta(minutes=25)},
                                 explanation=""))
        self.log_and_wait(Record(application="usage_stats",
                                 logger="desktop",
                                 datetime=datetime.now() - timedelta(minutes=4),
                                 level=levels["info"],
                                 msg="data",
                                 args={"keys": 3, "pixels": 1920},
                                 explanation=""))
        self.log_and_wait(Record(application="usage_stats",
                                 logger="desktop",
                                 datetime=datetime.now() - timedelta(minutes=3),
                                 level=levels["info"],
                                 msg="data",
                                 args={"keys": 3, "pixels": 1920},
                                 explanation=""))

    def more_awake(self):
        self.log_and_wait(Record(application="usage_stats",
                                 logger="desktop",
                                 datetime=datetime.now() - timedelta(minutes=2),
                                 level=levels["info"],
                                 msg="data",
                                 args={"keys": 3, "pixels": 1920},
                                 explanation=""))

    def test_http(self):
        self.write_script("analytics", "awake", self.awake)

        self.start(self.config)

        self.init_awake()
        response = self.performRequest("/analytics/awake")
        self.assertEqual(response["state"], "up")
        self.assertAlmostEqual(response["seconds_up"], 25 * 60, delta=1)
        self.assertAlmostEqual(response["seconds_pc"], 60, delta=1)

        self.more_awake()
        response = self.performRequest("/analytics/awake")
        self.assertEqual(response["state"], "up")
        self.assertAlmostEqual(response["seconds_up"], 25 * 60, delta=1)
        self.assertAlmostEqual(response["seconds_pc"], 120, delta=1)

    def test_websocket(self):
        self.write_script("analytics", "awake", self.awake)

        self.start(self.config)

        self.init_awake()
        reader = self.websocketReader("/analytics/awake")

        time.sleep(0.5)
        self.assertEqual(len(reader), 1)
        self.assertEqual(reader[-1]["state"], "up")
        self.assertAlmostEqual(reader[-1]["seconds_up"], 25 * 60, delta=1)
        self.assertAlmostEqual(reader[-1]["seconds_pc"], 60, delta=1)

        self.more_awake()
        time.sleep(0.5)
        self.assertEqual(len(reader), 2)
        self.assertEqual(reader[-1]["state"], "up")
        self.assertAlmostEqual(reader[-1]["seconds_up"], 25 * 60, delta=1)
        self.assertAlmostEqual(reader[-1]["seconds_pc"], 120, delta=1)

    def test_websocket_with_now(self):
        awake_hb = self.awake
        awake_hb = awake_hb.replace("def analyze(last_sleep_track, odometer_logs):",
                                    "def analyze(last_sleep_track, odometer_logs, now):")
        awake_hb = awake_hb.replace("now = datetime.now()",
                                    "")
        self.write_script("analytics", "awake", awake_hb)

        self.start(self.config)

        self.init_awake()
        reader = self.websocketReader("/analytics/awake")

        time.sleep(0.5)
        self.assertEqual(reader[-1]["state"], "up")
        self.assertAlmostEqual(reader[-1]["seconds_up"], 25 * 60, delta=1)
        self.assertAlmostEqual(reader[-1]["seconds_pc"], 60, delta=1)

        time.sleep(5)
        self.assertEqual(reader[-1]["state"], "up")
        self.assertAlmostEqual(reader[-1]["seconds_up"], 25 * 60 + 5, delta=1)
        self.assertAlmostEqual(reader[-1]["seconds_pc"], 60, delta=1)

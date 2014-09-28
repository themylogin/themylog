# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import operator
from testfixtures import replace
import unittest

from themylog.config.analytics import BadParameterArgumentException, order_feeds, calculate_feed_dependencies
from themylog.rules_tree import Param as P, RecordField as F


class OrderFeedsTestCase(unittest.TestCase):
    dependencies_mock = lambda d: set(d.get("params", []))

    @replace("themylog.config.analytics.calculate_feed_dependencies", dependencies_mock)
    def test_simple_order(self):
        self.assertEqual(order_feeds({"last_sleep_track": {},
                                      "odometer_logs": {"params": ["last_sleep_track"]}}),
                         ["last_sleep_track", "odometer_logs"])

    @replace("themylog.config.analytics.calculate_feed_dependencies", dependencies_mock)
    def test_raises_bad_parameter_argument_exception(self):
        self.assertRaises(BadParameterArgumentException, lambda: order_feeds({"last_sleep_track": {},
                                                                              "odometer_logs": {"params": ["last_sleep_trick"]}}))



class CalculateFeedDependenciesTestCase(unittest.TestCase):
    def test_empty_dependencies(self):
        desc = {"rules_tree": (operator.and_, (operator.eq, F("logger"), "sleep_tracker"),
                                              (operator.or_, (operator.eq, F("msg"), "woke_up"),
                                                             (operator.eq, F("msg"), "fall_asleep"))),
                "limit": 1}
        self.assertEqual(calculate_feed_dependencies(desc), set())

    def test_one_dependency(self):
        desc = {"rules_tree": (operator.and_, (operator.eq, F("application"), "usage_stats"),
                                              (operator.gt, F("datetime"), P("last_sleep_track_datetime"))),
                "params": {"last_sleep_track_datetime": lambda last_sleep_track: last_sleep_track.args["at"]
                                                                                 if last_sleep_track.msg == "woke_up"
                                                                                 else 9000}}
        self.assertEqual(calculate_feed_dependencies(desc), {"last_sleep_track"})

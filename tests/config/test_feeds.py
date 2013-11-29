import operator
import unittest

import themylog.config as config
from themylog.level import levels

class FeedConditionPartTestCase(unittest.TestCase):
    def expectResult(self, config_key, config_value, op, record_key, value):
        t = config.get_feed_tree_condition_part(config_key, config_value)
        self.assertEqual(t[0], op)
        self.assertEqual(t[1](lambda x: x), record_key)
        self.assertEqual(t[2], value)
        self.assertEqual(len(t), 3)

    def test_simple_eq(self):
        self.expectResult("source", "sync_scrobbles_daemon",
                          operator.eq, "source", "sync_scrobbles_daemon")

    def test_simple_le(self):
        self.expectResult("some_numeric_key", "<= 5",
                          operator.le, "some_numeric_key", 5)

    def test_level(self):
        self.expectResult("level", "> info",
                          operator.gt, "level", levels["info"])

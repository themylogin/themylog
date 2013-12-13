from mock import Mock
import textwrap
import unittest
import yaml

from themylog.config import get_feed
from themylog.level import levels


class FeedContainsTestCase(unittest.TestCase):
    def create_feed_from_yaml(self, feed_yaml):
        return get_feed(yaml.load(textwrap.dedent(feed_yaml)))

    def expect_feed_contains_record(self, feed, record_dict, contains):
        record = Mock
        for k, v in record_dict.items():
            setattr(record, k, v)

        self.assertEqual(feed.contains(record), contains)

    def test_no_action(self):
        self.assertRaises(Exception, self.create_feed_from_yaml, """
            -
                level: < report
        """)

    def test_simple_reject(self):
        f = self.create_feed_from_yaml("""
            -
                level: < report
                action: reject
        """)

        self.expect_feed_contains_record(f, {"level": levels["info"]}, False)
        self.expect_feed_contains_record(f, {"level": levels["report"]}, True)

    def test_simple_accept(self):
        f = self.create_feed_from_yaml("""
            -
                level: ">= report"
                action: accept
            -
                action: reject
        """)

        self.expect_feed_contains_record(f, {"level": levels["info"]}, False)
        self.expect_feed_contains_record(f, {"level": levels["report"]}, True)

    def test_simple_reject_with_multiple_keys(self):
        f = self.create_feed_from_yaml("""
            -
                application: sync_scrobbles_daemon
                level: < warning
                action: reject
        """)

        self.expect_feed_contains_record(f, {"application": "smarthome", "level": levels["info"]}, True)
        self.expect_feed_contains_record(f, {"application": "sync_scrobbles_daemon", "level": levels["info"]}, False)
        self.expect_feed_contains_record(f, {"application": "sync_scrobbles_daemon", "level": levels["warning"]}, True)

    def test_multiple_reject(self):
        f = self.create_feed_from_yaml("""
            -
                level: < info
                action: reject
            -
                application: sync_scrobbles_daemon
                level: < warning
                action: reject
        """)

        self.expect_feed_contains_record(f, {"application": "smarthome", "level": levels["info"]}, True)
        self.expect_feed_contains_record(f, {"application": "smarthome", "level": levels["debug"]}, False)
        self.expect_feed_contains_record(f, {"application": "sync_scrobbles_daemon", "level": levels["info"]}, False)
        self.expect_feed_contains_record(f, {"application": "sync_scrobbles_daemon", "level": levels["warning"]}, True)

    def test_in_list(self):
        f = self.create_feed_from_yaml("""
            -
                application: [paramiko.transport, werkzeug]
                action: reject
        """)

        self.expect_feed_contains_record(f, {"application": "paramiko.transport"}, False)
        self.expect_feed_contains_record(f, {"application": "werkzeug"}, False)
        self.expect_feed_contains_record(f, {"application": "smarthome"}, True)

    def test_not_list(self):
        f = self.create_feed_from_yaml("""
            -
                application: "!= [paramiko.transport, werkzeug]"
                action: accept
            -
                action: reject
        """)

        self.expect_feed_contains_record(f, {"application": "paramiko.transport"}, False)
        self.expect_feed_contains_record(f, {"application": "werkzeug"}, False)
        self.expect_feed_contains_record(f, {"application": "smarthome"}, True)

    def test_bad_list_operator(self):
        self.assertRaises(ValueError, self.create_feed_from_yaml, """
            -
                application: < [paramiko.transport, werkzeug]
                action: reject
        """)

    def test_common_and_quotient_begins_with_accept(self):
        f = self.create_feed_from_yaml("""
            -
                application: smarthome
                logger: bell
                action: accept
            -
                application: smarthome
                action: reject
            -
                application: werkzeug
                action: reject
        """)

        self.expect_feed_contains_record(f, {"application": "smarthome", "logger": "bell"}, True)
        self.expect_feed_contains_record(f, {"application": "smarthome", "logger": "bathroom_door"}, False)
        self.expect_feed_contains_record(f, {"application": "werkzeug"}, False)
        self.expect_feed_contains_record(f, {"application": "serega"}, True)

    def test_common_and_quotient_begins_with_reject(self):
        f = self.create_feed_from_yaml("""
            -
                application: smarthome
                logger: bell
                msg: up
                action: reject
            -
                application: smarthome
                logger: bell
                action: accept
            -
                application: smarthome
                action: reject
            -
                application: werkzeug
                action: reject
        """)

        self.expect_feed_contains_record(f, {"application": "smarthome", "logger": "bell", "msg": "down"}, True)
        self.expect_feed_contains_record(f, {"application": "smarthome", "logger": "bell", "msg": "up"}, False)
        self.expect_feed_contains_record(f, {"application": "smarthome", "logger": "bathroom_door"}, False)
        self.expect_feed_contains_record(f, {"application": "werkzeug"}, False)
        self.expect_feed_contains_record(f, {"application": "serega"}, True)

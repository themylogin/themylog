from mock import Mock
import textwrap
import unittest
import yaml

from themylog.config import get_feed
from themylog.level import levels


class FeedContainsTestCase(unittest.TestCase):
    def createFeedFromYaml(self, feed_yaml):
        return get_feed(yaml.load(textwrap.dedent(feed_yaml)))

    def expectFeedContainsRecord(self, feed, record_dict, contains):
        record = Mock
        for k, v in record_dict.items():
            setattr(record, k, v)

        self.assertEqual(feed.contains(record), contains)

    def test_simple_reject(self):
        f = self.createFeedFromYaml("""
            -
                level: < report
                action: reject
        """)

        self.expectFeedContainsRecord(f, {"level": levels["info"]}, False)
        self.expectFeedContainsRecord(f, {"level": levels["report"]}, True)

    def test_simple_accept(self):
        f = self.createFeedFromYaml("""
            -
                level: ">= report"
                action: accept
            -
                action: reject
        """)

        self.expectFeedContainsRecord(f, {"level": levels["info"]}, False)
        self.expectFeedContainsRecord(f, {"level": levels["report"]}, True)

    def test_simple_reject_with_multiple_keys(self):
        f = self.createFeedFromYaml("""
            -
                application: sync_scrobbles_daemon
                level: < warning
                action: reject
        """)

        self.expectFeedContainsRecord(f, {"application": "smarthome", "level": levels["info"]}, True)
        self.expectFeedContainsRecord(f, {"application": "sync_scrobbles_daemon", "level": levels["info"]}, False)
        self.expectFeedContainsRecord(f, {"application": "sync_scrobbles_daemon", "level": levels["warning"]}, True)

    def test_multiple_reject(self):
        f = self.createFeedFromYaml("""
            -
                level: < info
                action: reject
            -
                application: sync_scrobbles_daemon
                level: < warning
                action: reject
        """)

        self.expectFeedContainsRecord(f, {"application": "smarthome", "level": levels["info"]}, True)
        self.expectFeedContainsRecord(f, {"application": "smarthome", "level": levels["debug"]}, False)
        self.expectFeedContainsRecord(f, {"application": "sync_scrobbles_daemon", "level": levels["info"]}, False)
        self.expectFeedContainsRecord(f, {"application": "sync_scrobbles_daemon", "level": levels["warning"]}, True)

    def test_in_list(self):
        f = self.createFeedFromYaml("""
            -
                application: [paramiko.transport, werkzeug]
                action: reject
        """)

        self.expectFeedContainsRecord(f, {"application": "paramiko.transport"}, False)
        self.expectFeedContainsRecord(f, {"application": "werkzeug"}, False)
        self.expectFeedContainsRecord(f, {"application": "smarthome"}, True)

    def test_not_list(self):
        f = self.createFeedFromYaml("""
            -
                application: "!= [paramiko.transport, werkzeug]"
                action: accept
            -
                action: reject
        """)

        self.expectFeedContainsRecord(f, {"application": "paramiko.transport"}, False)
        self.expectFeedContainsRecord(f, {"application": "werkzeug"}, False)
        self.expectFeedContainsRecord(f, {"application": "smarthome"}, True)

    def test_bad_list_operator(self):
        self.assertRaises(ValueError, self.createFeedFromYaml, """
            -
                application: < [paramiko.transport, werkzeug]
                action: reject
        """)

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

    def test_simple_exclude(self):
        f = self.createFeedFromYaml("""
        exclude:
            -
                level: < report
        """)

        self.expectFeedContainsRecord(f, {"level": levels["info"]}, False)
        self.expectFeedContainsRecord(f, {"level": levels["report"]}, True)

    def test_simple_include(self):
        f = self.createFeedFromYaml("""
        include:
            -
                level: ">= report"
        """)

        self.expectFeedContainsRecord(f, {"level": levels["info"]}, False)
        self.expectFeedContainsRecord(f, {"level": levels["report"]}, True)

    def test_simple_exclude_with_multiple_keys(self):
        f = self.createFeedFromYaml("""
        exclude:
            -
                source: sync_scrobbles_daemon
                level: < warning

        """)

        self.expectFeedContainsRecord(f, {"source": "smarthome", "level": levels["info"]}, True)
        self.expectFeedContainsRecord(f, {"source": "sync_scrobbles_daemon", "level": levels["info"]}, False)
        self.expectFeedContainsRecord(f, {"source": "sync_scrobbles_daemon", "level": levels["warning"]}, True)

    def test_compound_exclude(self):
        f = self.createFeedFromYaml("""
        exclude:
            -
                level: < info
            -
                source: sync_scrobbles_daemon
                level: < warning
        """)

        self.expectFeedContainsRecord(f, {"source": "smarthome", "level": levels["info"]}, True)
        self.expectFeedContainsRecord(f, {"source": "smarthome", "level": levels["debug"]}, False)
        self.expectFeedContainsRecord(f, {"source": "sync_scrobbles_daemon", "level": levels["info"]}, False)
        self.expectFeedContainsRecord(f, {"source": "sync_scrobbles_daemon", "level": levels["warning"]}, True)

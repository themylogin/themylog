import textwrap
import unittest

from themylog.level import levels
from themylog.record.parser import parse_plaintext


class PlaintextRecordParserTestCase(unittest.TestCase):
    def parse(self, text):
        return parse_plaintext(textwrap.dedent(text).strip())

    def test_unknown_keys_to_args(self):
        record = self.parse("""
            application=test_application
            logger=test_logger
            level=info
            msg=test
            key1=1
            key2=1.1
            key3=Test key
        """)
        self.assertEqual(record.application, "test_application")
        self.assertEqual(record.logger, "test_logger")
        self.assertEqual(record.level, levels["info"])
        self.assertEqual(record.msg, "test")
        self.assertEqual(record.args, {"key1": 1, "key2": 1.1, "key3": "Test key"})

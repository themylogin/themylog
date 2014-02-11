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

    def test_args_lists(self):
        record = self.parse("""
            msg=test
            list[0]=5
            list[1]=25
            list[2]=125
        """)
        self.assertEqual(record.msg, "test")
        self.assertEqual(record.args, {"list": [5, 25, 125]})

    def test_args_lists_unordered_keys(self):
        record = self.parse("""
            msg=test
            list[2]=125
            list[0]=5
            list[1]=25
        """)
        self.assertEqual(record.msg, "test")
        self.assertEqual(record.args, {"list": [5, 25, 125]})

    def test_args_lists_skipped_keys(self):
        record = self.parse("""
            msg=test
            list[0]=5
            list[2]=625
            list[6]=15625
        """)
        self.assertEqual(record.msg, "test")
        self.assertEqual(record.args, {"list": [5, None, 625, None, None, None, 15625]})

    def test_equal_sign_in_arg_value(self):
        record = self.parse("""
            msg=test
            titles[1]=a=b
        """)
        self.assertEqual(record.msg, "test")
        self.assertEqual(record.args, {"titles": [None, "a=b"]})


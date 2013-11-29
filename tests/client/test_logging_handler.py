import logging
import unittest

from themylog.client import LoggingHandler

class GetLevelTestCase(unittest.TestCase):
    def create_fake_record(self, **kwargs):
        record_kwargs = dict(name="root",
                             level=logging.NOTSET,
                             pathname="/fake.py",
                             lineno=1,
                             msg="",
                             args=(),
                             exc_info=None,
                             func="fake")

        record_kwargs.update(kwargs)

        return logging.LogRecord(**record_kwargs)

    def test_ordinary_record(self):
        h = LoggingHandler(None)
        r = self.create_fake_record(level=logging.WARNING)
        self.assertEqual(h._get_level(r), "warning")

    def test_exception_record(self):
        h = LoggingHandler(None, exception_level="error")
        r = self.create_fake_record(level=logging.WARNING, exc_info=(Exception,))
        self.assertEqual(h._get_level(r), "error")

    def test_record_from_specific_logger(self):
        h = LoggingHandler(None, loggers_levels={"a": "debug", "b": "info"})
        r = self.create_fake_record(level=logging.WARNING)
        r_a = self.create_fake_record(level=logging.WARNING, name="a")
        r_b = self.create_fake_record(level=logging.WARNING, name="b")
        self.assertEqual(h._get_level(r), "warning")
        self.assertEqual(h._get_level(r_a), "debug")
        self.assertEqual(h._get_level(r_b), "info")

    def test_exception_record_from_specific_logger(self):
        h = LoggingHandler(None, loggers_levels={"a": "debug"})
        r = self.create_fake_record(name="a", level=logging.WARNING)
        r_e = self.create_fake_record(name="a", level=logging.WARNING, exc_info=(Exception,))
        self.assertEqual(h._get_level(r), "debug")
        self.assertEqual(h._get_level(r_e), "debug")


class UnderscoreMessageTestCase(unittest.TestCase):
    def setUp(self):
        self.h = LoggingHandler(None)

    def test_underscoring_works(self):
        self.assertEqual(self.h._underscore_message("Inserted %d scrobbles for %s"), "inserted_d_scrobbles_for_s")

    def test_trailing_underscore_strip(self):
        self.assertEqual(self.h._underscore_message("update_scrobbles('%s', asap=%r)"), "update_scrobbles_s_asap_r")

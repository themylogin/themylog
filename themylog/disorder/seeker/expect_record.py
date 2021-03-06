# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
from zope.interface import implements

from themyutils.datetime import russian_strftime
from themyutils.datetime.timedelta import timedelta_in_words

from themylog.disorder import Disorder
from themylog.disorder.seeker.abstract import AbstractDisorderSeeker
from themylog.disorder.seeker.interface import IDisorderSeeker, IReplayable
from themylog.rules_tree import match_record

__all__ = [b"ExpectRecordSeeker"]


class ExpectRecordSeeker(AbstractDisorderSeeker):
    implements(IDisorderSeeker, IReplayable)

    def __init__(self, condition, interval):
        self.condition = condition
        self.interval = interval

    def receive_record(self, record):
        if match_record(self.condition, record):
            if record.datetime >= datetime.now() - self.interval:
                self.there_is_no_disorder(Disorder(record.datetime, self._disorder_reason(record), {"record": record}))
            else:
                p = "Больше, чем %s назад, " % timedelta_in_words(self.interval, 2)
                self.there_is_disorder(Disorder(datetime.now(), p + self._disorder_reason(record), {"record": record}))

    def replay(self, retriever):
        records = retriever.retrieve(self.condition, 1)
        if records:
            self.receive_record(records[0])

    def _disorder_reason(self, record):
        reason = "%s в %s" % (russian_strftime(record.datetime, "%e %B").strip(), record.datetime.strftime("%H:%M"))
        if record.explanation != "":
            reason += " " + record.explanation[0].lower() + record.explanation[1:].strip()
        return reason

# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
from zope.interface import implements

from themylog.disorder import Disorder
from themylog.disorder.seeker.abstract import AbstractDisorderSeeker
from themylog.disorder.seeker.interface import IDisorderSeeker, IReplayable
from themylog.rules_tree import match_record

__all__ = ["RecordBasedSeeker"]


class ExpectRecordSeeker(AbstractDisorderSeeker):
    implements(IDisorderSeeker, IReplayable)

    def __init__(self, condition, interval):
        self.condition = condition
        self.interval = interval

    def receive_record(self, record):
        if match_record(self.condition, record) and record.datetime >= datetime.now() - self.interval:
            self.there_is_no_disorder(Disorder(record.datetime, None, {"record": record}))
        else:
            self.there_is_disorder(Disorder(datetime.now(),
                                            "Последняя запись %s" % record.datetime.strftime("%d.%m в %H:%M"),
                                            {}))

    def replay(self, retriever):
        records = retriever.retrieve(self.condition, 1)
        if records:
            self.receive_record(records[0])

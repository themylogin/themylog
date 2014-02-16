from __future__ import absolute_import

from datetime import datetime
import operator
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
            self.there_is_disorder(Disorder(datetime.now(), None, {}))

    def replay(self, retriever):
        records = retriever.retrieve((operator.and_,
                                         self.condition,
                                         (operator.ge, lambda k: k("datetime"), datetime.now() - self.interval)), 1)
        if records:
            self.there_is_no_disorder(Disorder(records[0].datetime, None, {"record": records[0]}))
        else:
            self.there_is_disorder(Disorder(datetime.now(), None, {}))

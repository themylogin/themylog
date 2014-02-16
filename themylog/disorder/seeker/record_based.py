from __future__ import absolute_import

from datetime import datetime
import operator
from zope.interface import implements

from themylog.disorder import Disorder
from themylog.disorder.seeker.abstract import AbstractDisorderSeeker
from themylog.disorder.seeker.interface import IDisorderSeeker, IReplayable
from themylog.rules_tree import match_record

__all__ = ["RecordBasedSeeker"]


class RecordBasedSeeker(AbstractDisorderSeeker):
    implements(IDisorderSeeker, IReplayable)

    def __init__(self, right, wrong, period=None):
        self.right = right
        self.wrong = wrong
        self.period = period

        self.last_seeker_record_received_at = None

    def receive_record(self, record):
        if match_record(self.right, record):
            self.there_is_no_disorder(Disorder(record.datetime, self.disorder_reason(record),
                                               {"record": record._asdict()}))
            self.last_seeker_record_received_at = record.datetime
        elif match_record(self.wrong, record):
            self.there_is_disorder(Disorder(record.datetime, self.disorder_reason(record),
                                            {"record": record._asdict()}))
            self.last_seeker_record_received_at = record.datetime
        else:
            if self.period is not None:
                if self.last_seeker_record_received_at is None or\
                        datetime.now() - self.period > self.last_seeker_record_received_at:
                    self.seeker_is_not_functional()

    def disorder_reason(self, record):
        if record.explanation:
            return record.explanation
        else:
            return "%s.%s.%s" % (record.application, record.logger, record.msg)

    def replay(self, retriever):
        records = retriever.retrieve((operator.or_, self.right, self.wrong), 1)
        if records:
            self.receive_record(records[0])
        else:
            self.seeker_is_not_functional()

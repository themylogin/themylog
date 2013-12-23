from __future__ import absolute_import

from datetime import datetime
from zope.interface import implements

from themylog.disorder.seeker.abstract import AbstractDisorderSeeker
from themylog.disorder.seeker.interface import IDisorderSeeker, IReplayable

__all__ = ["DisorderSeeker"]


class DisorderSeeker(AbstractDisorderSeeker):
    implements(IDisorderSeeker)

    def __init__(self, right, wrong, period=None):
        self.right = right
        self.wrong = wrong
        self.period = period

        self.last_seeker_record_received_at = None

    def receive_record(self, record):
        if self.wrong.contains(record):
            self.there_is_disorder(record)
            self.last_seeker_record_received_at = record.datetime
        elif self.right.contains(record):
            self.there_is_no_disorder(record)
            self.last_seeker_record_received_at = record.datetime
        else:
            if self.period is not None:
                if self.last_seeker_record_received_at is None or\
                                        datetime.now() - self.period > self.last_seeker_record_received_at:
                    self.seeker_is_not_functional()

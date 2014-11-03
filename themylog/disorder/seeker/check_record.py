# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from zope.interface import implements

from themylog.disorder import Disorder
from themylog.disorder.seeker.abstract import AbstractDisorderSeeker
from themylog.disorder.seeker.interface import IDisorderSeeker, IReplayable
from themylog.rules_tree import match_record

__all__ = [b"CheckRecordSeeker"]


class CheckRecordSeeker(AbstractDisorderSeeker):
    implements(IDisorderSeeker, IReplayable)

    def __init__(self, condition, function):
        self.condition = condition
        self.function = function

    def receive_record(self, record):
        if match_record(self.condition, record):
            has_no_disorder, reason = self.function(record)
            disorder = Disorder(record.datetime, reason, {"record": record})
            self.state_disorder(not has_no_disorder, disorder)

    def replay(self, retriever):
        records = retriever.retrieve(self.condition, 1)
        if records:
            self.receive_record(records[0])

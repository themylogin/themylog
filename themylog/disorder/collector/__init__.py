# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime, timedelta
import operator
from zope.interface import implements

from themylog.disorder import Disorder
from themylog.disorder.seeker.abstract import AbstractDisorderSeeker
from themylog.disorder.seeker.interface import IDisorderSeeker, IReplayable
from themylog.level import levels


def setup_collector_disorder_seekers(disorder_manager, collectors):
    for collector in collectors:
        disorder_manager.add(collector.annotations.get("title", "Обновление %s" % collector.name),
                             CollectorDisorderSeeker(collector))


class CollectorDisorderSeeker(AbstractDisorderSeeker):
    implements(IDisorderSeeker, IReplayable)

    def __init__(self, collector):
        self.collector = collector

    def receive_record(self, record):
        if record.application == "%s.collector" % self.collector.name:
            if record.level < levels["warning"]:
                self.there_is_no_disorder(Disorder(record.datetime, None, {"record": record._asdict()}))
            else:
                self.there_is_disorder(Disorder(record.datetime, None, {"record": record._asdict()}))

    def replay(self, retriever):
        records = retriever.retrieve((operator.and_,
                                         (operator.eq, lambda k: k("application"), "%s.collector" % self.collector.name),
                                         (operator.ge, lambda k: k("datetime"), datetime.now() - timedelta(hours=2))))
        if records:
            for record in records:
                if record.level < levels["warning"]:
                    self.there_is_no_disorder(Disorder(record.datetime, None, {"record": record._asdict()}))
                    break
            else:
                self.there_is_disorder(Disorder(record.datetime, None, {"record": record._asdict()}))
        else:
            self.seeker_is_not_functional()

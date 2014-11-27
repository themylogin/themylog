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

        self.allowed_downtime = self.collector.annotations.get("allowed_downtime", timedelta(hours=1))
        self.last_success = None

    def receive_record(self, record):
        if record.application == "%s.collector" % self.collector.name and record.logger == "collector":
            self._handle_record(record)

    def replay(self, retriever):
        records = retriever.retrieve(
            (operator.and_,
             (operator.eq, lambda k: k("application"), "%s.collector" % self.collector.name),
             (operator.and_,
              (operator.eq, lambda k: k("logger"), "collector"),
              (operator.ge, lambda k: k("datetime"), datetime.now() - timedelta(hours=24)))))
        if records:
            if not any(self._handle_record(record) for record in records):
                self.there_is_disorder(Disorder(records[0].datetime, None, {"record": records[0]}))
        else:
            self.seeker_is_not_functional()

    def _handle_record(self, record):
        if record.level >= levels["warning"]:
            if self.allowed_downtime is None or datetime.now() - record.datetime > self.allowed_downtime:
                self.there_is_disorder(Disorder(record.datetime, None, {"record": record}))
                return True
        else:
            self.there_is_no_disorder(Disorder(record.datetime, None, {"record": record}))
            return True

        return False

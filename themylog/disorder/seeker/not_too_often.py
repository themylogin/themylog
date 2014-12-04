# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import defaultdict, OrderedDict
from datetime import datetime
import operator
from pytils.numeral import get_plural
from zope.interface import implements

from themylog.disorder import Disorder, MaybeDisorder, maybe_with_title
from themylog.disorder.seeker.abstract import AbstractDisorderSeeker
from themylog.disorder.seeker.interface import IDisorderSeeker, IReplayable
from themylog.rules_tree import match_record

__all__ = [b"NotTooOftenSeeker"]


class NotTooOftenSeeker(AbstractDisorderSeeker):
    implements(IDisorderSeeker, IReplayable)

    def __init__(self, condition, interval, times, group_by=None):
        self.condition = condition
        self.interval = interval
        self.times = times
        self.group_by = group_by or (lambda record: None)

        self.group_to_times = defaultdict(list)


    def receive_record(self, record):
        if match_record(self.condition, record):
            self.group_to_times[self.group_by(record)].append(record)

        reason = OrderedDict()
        for group, items in sorted(self.group_to_times.iteritems(), key=lambda (g, m): g.lower()
                                                                                       if isinstance(g, (str, unicode))
                                                                                       else g):
            items = filter(lambda record: record.datetime > datetime.now() - self.interval, items)
            self.group_to_times[group] = items
            if len(items) > self.times:
                is_disorder = True
                disorder_datetime = items[self.times].datetime
            else:
                is_disorder = False
                disorder_datetime = items[-1].datetime
            reason[group] = MaybeDisorder(is_disorder, Disorder(
                disorder_datetime,
                "Событие произошло %s" % get_plural(len(items), ("раз", "раза", "раз")),
                {"records": items}
            ))

        if any(maybe.is_disorder for maybe in reason.values()):
            is_disorder = True
            disorder_datetime = min(maybe.disorder.datetime
                                    for maybe in reason.values()
                                    if maybe.is_disorder)
        else:
            is_disorder = False
            disorder_datetime = max(maybe.disorder.datetime for maybe in reason.values()) if reason else datetime.now()
        self.state_disorder(is_disorder, Disorder(
            disorder_datetime,
            ([maybe_with_title(maybe, group) for group, maybe in reason.iteritems()]
             if self.group_by else (reason.values()[0].disorder if reason.values() else "Неприятностей не произошло")),
            {"counts": {group: len(items)
             for group, items in self.group_to_times.iteritems()}}
             if self.group_by else {"count": len(self.group_to_times.values()[0])}
        ))

    def replay(self, retriever):
        records = retriever.retrieve((operator.and_,
                                      self.condition,
                                      (operator.ge, lambda k: k("datetime"), datetime.now() - self.interval)))
        if records:
            for record in reversed(records):
                self.receive_record(record)
        else:
            self.state_disorder(False, Disorder(datetime.now(), "Неприятностей не произошло", {}))

# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import defaultdict
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
            self.group_to_times[self.group_by(record)].append(record.datetime)

        reason = {}
        for group, items in self.group_to_times.iteritems():
            items = filter(lambda d: d > datetime.now() - self.interval, items)
            self.group_to_times[group] = items
            if len(items) > self.times:
                reason[group] = MaybeDisorder(True, Disorder(
                    items[-1],
                    "Событие произошло %s" % get_plural(len(items), ("раз", "раза", "раз")),
                    {"count": len(items)}
                ))

        if reason:
            if self.group_by:
                self.there_is_disorder(Disorder(min([maybe.disorder.datetime for maybe in reason.values()]),
                                                [maybe_with_title(maybe, group)
                                                 for group, maybe in sorted(reason.iteritems(),
                                                                            key=lambda (g, m): g.lower())],
                                                {}))
            else:
                self.there_is_disorder(reason.values()[0].disorder)
        else:
            self._state_no_disorder()

    def replay(self, retriever):
        records = retriever.retrieve((operator.and_,
                                      self.condition,
                                      (operator.ge, lambda k: k("datetime"), datetime.now() - self.interval)))
        if records:
            for record in reversed(records):
                self.receive_record(record)
        else:
            self._state_no_disorder()

    def _state_no_disorder(self):
        self.there_is_no_disorder(Disorder(datetime.now(), "Неприятностей не произошло",
                                               {"counts": {group: len(items)
                                                           for group, items in self.group_to_times.iteritems()}}
                                               if self.group_by else {"count": len(self.group_to_times.values()[0])}))

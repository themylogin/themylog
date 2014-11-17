# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
from zope.interface import implements

from themylog.disorder import Disorder, MaybeDisorder, maybe_with_title, IDisorderObserver
from themylog.disorder.seeker.abstract import AbstractDisorderSeeker
from themylog.disorder.seeker.interface import IDisorderSeeker, IReplayable

__all__ = [b"SeekerGroup"]


class SeekerGroup(AbstractDisorderSeeker):
    implements(IDisorderSeeker, IReplayable)

    def __init__(self, seekers):
        self.seekers = seekers

        self.observer = SeekerGroupObserver(self)
        for key, seeker in self.seekers.iteritems():
            seeker.add_observer(self.observer, key)

    def receive_record(self, record):
        for seeker in self.seekers.values():
            seeker.receive_record(record)

    def replay(self, retriever):
        for seeker in self.seekers.values():
            if IReplayable.providedBy(seeker):
                seeker.replay(retriever)


class SeekerGroupObserver(object):
    implements(IDisorderObserver)

    def __init__(self, seeker_group):
        self.seeker_group = seeker_group

        self.disorders = {}

    def there_is_disorder(self, key, disorder):
        self.disorders[key] = MaybeDisorder(True, disorder)
        self._bubble_disorders()

    def there_is_no_disorder(self, key, disorder):
        self.disorders[key] = MaybeDisorder(False, disorder)
        self._bubble_disorders()

    def seeker_is_not_functional(self, key):
        self.disorders[key] = None
        self._bubble_disorders()

    def _bubble_disorders(self):
        is_disorder = False
        disorder_datetime = None
        no_disorder_datetime = None
        reason = []
        data = {}

        for key in self.seeker_group.seekers:
            maybe = self.disorders.get(key)
            if maybe is None:
                is_disorder = True
                disorder_datetime = datetime.now()
                reason.append({"title": key, "disorder": None})
            else:
                if maybe.is_disorder:
                    is_disorder = True
                    if disorder_datetime is None or disorder_datetime > maybe.disorder.datetime:
                        disorder_datetime = maybe.disorder.datetime
                else:
                    if no_disorder_datetime is None or no_disorder_datetime < maybe.disorder.datetime:
                        no_disorder_datetime = maybe.disorder.datetime
                reason.append(maybe_with_title(maybe, key))

        if is_disorder:
            self.seeker_group.there_is_disorder(Disorder(disorder_datetime, reason, data))
        else:
            self.seeker_group.there_is_no_disorder(Disorder(no_disorder_datetime, reason, data))

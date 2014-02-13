# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import OrderedDict
from zope.interface import Interface, implements

from themylog.disorder.seeker.interface import IReplayable
from themylog.handler.interface import IHandler, IRetrieveCapable


class DisorderManager(object):
    implements(IHandler)

    def __init__(self, handlers):
        for handler in handlers:
            if IRetrieveCapable.providedBy(handler):
                self.retriever = handler
                break
        else:
            self.retriever = None

        handlers.append(self)

        self.seekers = {}
        self.disorders = OrderedDict()

        self.observers = []

    def add(self, key, seeker):
        seeker.add_observer(self, key)
        self.seekers[key] = seeker

        self.disorders[key] = None
        if self.retriever and IReplayable.providedBy(seeker):
            seeker.replay(self.retriever)

    def there_is_disorder(self, key, reason):
        self.set_disorder_value(key, (False, reason))

    def there_is_no_disorder(self, key, reason):
        self.set_disorder_value(key, (True, reason))

    def seeker_is_not_functional(self, key):
        self.set_disorder_value(key, None)

    def set_disorder_value(self, key, value):
        if value != self.disorders[key]:
            self.disorders[key] = value
            self.notify_observers()

    def add_observer(self, observer):
        self.observers.append(observer)
        observer.update_disorders(self.disorders.copy())

    def notify_observers(self):
        for observer in self.observers:
            observer.update_disorders(self.disorders.copy())

    def handle(self, record):
        for seeker in self.seekers.values():
            seeker.receive_record(record)


class IDisorderManagerObserver(Interface):
    def update_disorders(self, manager):
        """Update from manager"""

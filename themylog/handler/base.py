# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from itertools import count
import logging
from Queue import PriorityQueue
from threading import Event, Lock
import time
from zope.interface import implements

from themyutils.threading import start_daemon_thread

from themylog.handler.interface import IHandler

logger = logging.getLogger(__name__)

__all__ = [b"BaseHandler"]


class BaseHandler(object):
    implements(IHandler)

    REINITIALIZE_TIMEOUT = 5

    def __init__(self):
        self.queue = PriorityQueue()
        self.seq_lock = Lock()
        self.seq = count()

        start_daemon_thread(self._persister_thread)

    def handle(self, record):
        with self.seq_lock:
            seq = self.seq.next()

        result = Result()

        self.queue.put((seq, record, result))

        return result

    def _persister_thread(self):
        while True:
            try:
                self.initialize()

                while True:
                    seq, record, result = self.queue.get()
                    try:
                        value = self.process(record)
                    except Exception:
                        self.queue.put((seq, record, result))
                        raise
                    else:
                        result.set(value)
            except Exception:
                logger.getLogger(self.__class__.__name__).error("Exception in persister thread", exc_info=True)
                time.sleep(self.REINITIALIZE_TIMEOUT)

    def initialize(self):
        raise NotImplementedError

    def process(self, record):
        raise NotImplementedError


class Result(object):
    def __init__(self):
        self.event = Event()
        self.value = None

    def get(self):
        self.event.wait()
        return self.value

    def set(self, value):
        self.value = value
        self.event.set()

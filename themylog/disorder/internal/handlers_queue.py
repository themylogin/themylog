# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
import logging
from pytils.numeral import get_plural
import time
from zope.interface import implements

from themyutils.threading import start_daemon_thread

from themylog.disorder import Disorder
from themylog.disorder.seeker.abstract import AbstractDisorderSeeker
from themylog.disorder.seeker.interface import IDisorderSeeker

logger = logging.getLogger(__name__)

__all__ = [b"HandlersQueueDisorderSeeker"]


class HandlersQueueDisorderSeeker(AbstractDisorderSeeker):
    implements(IDisorderSeeker)

    def __init__(self, handler_manager):
        self.handler_manager = handler_manager
        start_daemon_thread(self._poll_queues)

    def receive_record(self, record):
        pass

    def _poll_queues(self):
        while True:
            now = datetime.now()
            disorders = [(lambda size: {"is_disorder": size > 10,
                                        "disorder": {"datetime": now,
                                                     "reason": "%s в очереди" % get_plural(size, ("запись", "записи", "записей"), "Нет записей"),
                                                     "data": {}},
                                        "title": name})
                         (queue.qsize())
                         for name, queue in self.handler_manager.queues.items()]
            self.state_disorder(any(disorder["is_disorder"] for disorder in disorders),
                                Disorder(now, disorders, {}))

            time.sleep(10)

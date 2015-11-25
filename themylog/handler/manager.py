# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import functools
import logging
import time

from themyutils.threading import start_daemon_thread

logger = logging.getLogger(__name__)

__all__ = [b"HandlerManager"]


class HandlerManager(object):
    def __init__(self, record_fanout, queue_factory):
        self.record_fanout = record_fanout
        self.queue_factory = queue_factory

        self.handlers = {}
        self.queues = {}

    def add_handler(self, name, handler):
        queue = self.queue_factory(name)
        self.record_fanout.add_queue(queue)

        start_daemon_thread(functools.partial(self._handler_thread, name, handler, queue))

        self.handlers[name] = handler
        self.queues[name] = queue

    def _handler_thread(self, name, handler, queue):
        logger = logging.getLogger("handler.%s" % name)

        while True:
            try:
                handler.initialize()

                while True:
                    handler.process(queue.peek())
                    queue.get()
            except Exception:
                logger.error("Exception in handler thread", exc_info=True)
                time.sleep(5)

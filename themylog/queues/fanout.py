# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging

logger = logging.getLogger(__name__)

__all__ = [b"Fanout"]


class Fanout(object):
    def __init__(self):
        self.queues = []

    def add_queue(self, queue):
        self.queues.append(queue)

    def put(self, item):
        for queue in list(self.queues):
            queue.put(item)

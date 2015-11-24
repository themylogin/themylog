# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import namedtuple
import copy
import functools
import logging
from Queue import Queue

logger = logging.getLogger(__name__)

__all__ = [b"Fanout"]

FanoutTask = namedtuple("FanoutTask", ["item", "on_finish"])
FanoutIterJoinResult = namedtuple("FanoutIterJoinResult", ["queue_name", "result"])


class Fanout(object):
    def __init__(self, queues):
        self.queues = queues

    def put(self, item):
        target_queues = copy.copy(self.queues.items())
        result = FanoutResult(len(target_queues))
        for queue_name, queue in target_queues:
            queue.put(FanoutTask(item, functools.partial(result.notify, queue_name)))
        return result


class FanoutResult(object):
    def __init__(self, n):
        self.result_queue = Queue()

        self.wait_queue = Queue()
        [self.wait_queue.put(None) for _ in range(n)]

    def notify(self, queue_name, result):
        self.result_queue.put(FanoutIterJoinResult(queue_name, result))

        self.wait_queue.get()
        self.wait_queue.task_done()

    def join(self):
        return self.wait_queue.join()

    def iterjoin(self):
        while not self.wait_queue.empty():
            yield self.result_queue.get()

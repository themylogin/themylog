# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
import Queue
import threading

from themyutils.threading import start_daemon_thread

logger = logging.getLogger(__name__)

__all__ = [b"WorkerPool"]


class WorkerPool(object):
    def __init__(self, name=None):
        self.logger = logger.getChild(name) if name is not None else logger
        self.total_workers = 0
        self.busy_workers = 0
        self.workers_lock = threading.Lock()
        self.queue = Queue.Queue()

    def run(self, task):
        with self.workers_lock:
            if not (self.busy_workers < self.total_workers):
                self.logger.info("Starting worker #%d", self.total_workers)
                start_daemon_thread(self._worker)
                self.total_workers += 1

        self.queue.put(task)

    def _worker(self):
        while True:
            task = self.queue.get()

            with self.workers_lock:
                self.busy_workers += 1

            try:
                task()
            except:
                self.logger.exception("Exception in worker_pool")

            with self.workers_lock:
                self.busy_workers -= 1

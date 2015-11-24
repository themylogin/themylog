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

    def initialize(self):
        raise NotImplementedError

    def process(self, record):
        raise NotImplementedError

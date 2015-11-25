# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
from zope.interface import implements

from themylog.handler.interface import IHandler

logger = logging.getLogger(__name__)

__all__ = [b"BaseHandler"]


class BaseHandler(object):
    implements(IHandler)

    REINITIALIZE_TIMEOUT = 5

    def initialize(self):
        pass

    def process(self, record):
        raise NotImplementedError

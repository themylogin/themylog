# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
from zope.interface import implements

from themylog.handler.base import BaseHandler
from themylog.handler.interface import IHandler
from themylog.processor import run_processor

logger = logging.getLogger(__name__)

__all__ = [b"ProcessorRunner"]


class ProcessorRunner(BaseHandler):
    implements(IHandler)

    def __init__(self, processor, record_fanout):
        self.processor = processor
        self.record_fanout = record_fanout

    def process(self, record):
        for new_record in run_processor(self.processor, record):
            self.record_fanout.put(new_record)

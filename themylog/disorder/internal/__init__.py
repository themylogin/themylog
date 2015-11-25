# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging

from themylog.disorder.internal.handlers_queue import HandlersQueueDisorderSeeker

logger = logging.getLogger(__name__)

__all__ = [b"setup_internal_disorder_seekers"]


def setup_internal_disorder_seekers(disorder_manager, handler_manager):
    disorder_manager.add("Очереди обработчиков", HandlersQueueDisorderSeeker(handler_manager))

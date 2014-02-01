# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from celery.schedules import crontab
from datetime import datetime

from themylog.config.handlers import create_handlers
from themylog.config.cleanup import get_cleanups
from themylog.handler.interface import ICleanupCapable


def setup_cleanup(celery, config):
    cleanups = get_cleanups(config)
    if cleanups:
        handlers = create_handlers(config)
        handlers = filter(lambda handler: ICleanupCapable.providedBy(handler), handlers)
        if not handlers:
            raise Exception("You don't have any handlers that are ICleanupCapable")

        def cleanup():
            for period, feed in cleanups:
                older_than = datetime.now() - period
                for handler in handlers:
                    handler.cleanup(feed, older_than)

        cleanup_task = celery.task(cleanup)

        celery.conf.CELERYBEAT_SCHEDULE[cleanup_task.name] = {
            "task":     cleanup_task.name,
            "schedule": crontab(minute="0"),
        }

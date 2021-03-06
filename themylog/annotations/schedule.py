# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from celery.schedules import crontab

from themylog.annotations import function_annotation


def schedule(tree):
    return function_annotation(tree, "crontab", crontab)

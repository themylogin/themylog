# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import timedelta

from themylog.annotations import function_annotation


def allowed_downtime(tree):
    return function_annotation(tree, "allowed_downtime", timedelta)

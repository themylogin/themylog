# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from themylog.annotations.schedule import schedule
from themylog.annotations.title import title
from themylog.annotations.timeout import timeout
from themylog.config.scripts import find_scripts


def get_collectors(config):
    return find_scripts(config.get("collectors", {}).get("directory"), {
        "schedule":     schedule,
        "title":        title,
        "timeout":      timeout,
    })

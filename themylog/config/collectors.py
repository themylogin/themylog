# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from themylog.annotations.allowed_downtime import allowed_downtime
from themylog.annotations.schedule import schedule
from themylog.annotations.title import title
from themylog.annotations.timeout import timeout
from themylog.config.scripts import find_scripts


def get_collectors(config):
    return find_scripts(config.get("collectors", {}).get("directory"), {
        "allowed_downtime":     allowed_downtime,
        "schedule":             schedule,
        "title":                title,
        "timeout":              timeout,
    })

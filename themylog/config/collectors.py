# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import namedtuple
import os

from themylog.annotations import read_annotations
from themylog.annotations.schedule import schedule

Collector = namedtuple("Collector", ["name", "path", "annotations"])


def get_collectors(config):
    collectors = []
    config_collectors = config.get("collectors")
    if config_collectors:
        for collector in os.listdir(config_collectors["directory"]):
            path = os.path.join(config_collectors["directory"], collector)
            name, ext = os.path.splitext(collector)

            if ext != ".py":
                continue

            annotations = read_annotations(open(path).read().decode("utf-8"), {
                "schedule":     schedule,
            })

            collectors.append(Collector(name=name, path=path, annotations=annotations))

    return collectors

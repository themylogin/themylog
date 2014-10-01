# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import namedtuple
from functools import reduce
import inspect
import sys

from themyutils.math.graph import toposort

from themylog.config.scripts import find_scripts

Analytics = namedtuple("Analytics", ["annotations", "feeds", "feeds_dependencies", "feeds_order", "analyze"])


class BadParameterArgumentException(Exception):
    pass


def get_analytics(config):
    analytics = {}
    directory = config.get("analytics", {}).get("directory")
    if directory:
        sys.path.insert(0, directory)
        for script in find_scripts(directory, {}):
            imported = __import__(script.name)
            feeds_dependencies = {name: calculate_feed_dependencies(desc)
                                  for name, desc in imported.feeds.iteritems()}
            analytics[script.name] = Analytics(annotations=script.annotations,
                                               feeds=imported.feeds,
                                               feeds_dependencies=feeds_dependencies,
                                               feeds_order=order_feeds(imported.feeds, feeds_dependencies),
                                               analyze=imported.analyze)
    return analytics


def order_feeds(feeds_dict, feeds_dependencies):
    feeds = []
    for layer in toposort(feeds_dependencies):
        for feed in layer:
            if feed not in feeds_dict:
                raise BadParameterArgumentException(feed)
            feeds.append(feed)
    return feeds


def calculate_feed_dependencies(desc):
    return set(reduce(sum, [inspect.getargspec(func).args for name, func in desc.get("params", {}).iteritems()], []))

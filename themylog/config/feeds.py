# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from themylog.config.rules_tree import get_rules_tree
from themylog.feed import Feed


def get_feeds(config):
    return {feed: get_feed(rules) for feed, rules in config.get("feeds", {}).items()}


def get_feed(rules):
    return Feed(get_rules_tree(rules))

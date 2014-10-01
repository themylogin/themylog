# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
import inspect

from themylog.rules_tree import substitute_parameters

__all__ = [b"get_analytics_kwargs", b"get_analytics_kwarg", b"prepare_analytics_rules_tree",
           b"process_analytics_special_kwargs"]


def get_analytics_kwargs(analytics, retriever):
    kwargs = {}
    for feed in analytics.feeds_order:
        kwargs[feed] = get_analytics_kwarg(analytics, retriever, kwargs, feed)

    process_analytics_special_kwargs(analytics, kwargs)

    return kwargs


def get_analytics_kwarg(analytics, retriever, kwargs, feed):
    rules_tree = prepare_analytics_rules_tree(analytics, feed, kwargs)
    limit = analytics.feeds[feed].get("limit", None)
    kwarg = retriever.retrieve(rules_tree, limit)
    if limit == 1:
        if len(kwarg):
            kwarg = kwarg[0]
        else:
            kwarg = None
    return kwarg


def prepare_analytics_rules_tree(analytics, feed, kwargs):
    params = {param: func(**{arg: kwargs[arg] for arg in inspect.getargspec(func).args})
              for param, func in analytics.feeds[feed].get("params", {}).iteritems()}
    rules_tree = substitute_parameters(analytics.feeds[feed]["rules_tree"], params)
    return rules_tree


def process_analytics_special_kwargs(analytics, kwargs):
    modified = set()

    if "now" in inspect.getargspec(analytics.analyze).args:
        kwargs["now"] = datetime.now()
        modified.add("now")

    return modified

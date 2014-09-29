# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
import inspect

from themylog.rules_tree import substitute_parameters

__all__ = [b"get_analytics_kwargs", b"prepare_analytics_rules_tree", b"process_analytics_special_kwargs"]


def get_analytics_kwargs(analytics, retriever):
    kwargs = {}
    for feed in analytics.feeds_order:
        rules_tree = prepare_analytics_rules_tree(analytics, feed, kwargs)
        limit = analytics.feeds[feed].get("limit", None)
        kwargs[feed] = retriever.retrieve(rules_tree, limit)
        if limit == 1:
            if len(kwargs[feed]):
                kwargs[feed] = kwargs[feed][0]
            else:
                kwargs[feed] = None

    process_analytics_special_kwargs(analytics, kwargs)

    return kwargs


def prepare_analytics_rules_tree(analytics, feed, kwargs):
    params = {param: func(**{arg: kwargs[arg] for arg in inspect.getargspec(func).args})
              for param, func in analytics.feeds[feed].get("params", {}).iteritems()}
    rules_tree = substitute_parameters(analytics.feeds[feed]["rules_tree"], params)
    return rules_tree

def process_analytics_special_kwargs(analytics, kwargs):
    modified = False

    if "now" in inspect.getargspec(analytics.analyze).args:
        kwargs["now"] = datetime.now()
        modified = True

    return modified

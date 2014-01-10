from __future__ import absolute_import

import zope.interface

from themylog.rules_tree import match_record


class Feed(object):
    def __init__(self, rules_tree):
        self.rules_tree = rules_tree

    def contains(self, record):
        return match_record(self.rules_tree, record)


class IFeedsAware(zope.interface.Interface):
    def set_feeds(self, feeds):
        pass

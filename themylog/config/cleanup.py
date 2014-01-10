from __future__ import absolute_import

import isodate

from themylog.config.feeds import get_rules_tree


def get_cleanups(config):
    return [(isodate.parse_duration(cleanup["period"]), get_rules_tree(cleanup["records"]))
            for cleanup in config.get("cleanup", [])]

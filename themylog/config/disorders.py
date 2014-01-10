from __future__ import absolute_import

import isodate

from themylog.config.rules_tree import get_rules_tree
from themylog.disorder import Disorder
import themylog.disorder.seeker


def get_disorders(config):
    return {k: get_disorder(**v) for k, v in config.get("disorders", []).items()}


def get_disorder(title, **kwargs):
    kwargs["right"] = get_rules_tree(kwargs["right"])
    kwargs["wrong"] = get_rules_tree(kwargs["wrong"])
    if "period" in kwargs:
        kwargs["period"] = isodate.parse_duration(kwargs["period"])

    return Disorder(title, themylog.disorder.seeker.DisorderSeeker(**kwargs))

from __future__ import absolute_import

import isodate


from themylog.annotations.schedule import schedule
from themylog.annotations.title import title
from themylog.config.rules_tree import get_rules_tree
from themylog.config.scripts import find_scripts
from themylog.disorder.manager import DisorderManager
from themylog.disorder.seeker.record_based import RecordBasedSeeker


def get_disorders(config, handlers):
    config_disorders = config.get("disorders", {})

    disorder_manager = DisorderManager(handlers)

    script_disorders = find_scripts(config_disorders.get("directory"), {
        "schedule":     schedule,
        "title":        title,
    })

    return disorder_manager, script_disorders


def get_record_based_disorder_seeker(title, **kwargs):
    kwargs["right"] = get_rules_tree(kwargs["right"])
    kwargs["wrong"] = get_rules_tree(kwargs["wrong"])
    if "period" in kwargs:
        kwargs["period"] = isodate.parse_duration(kwargs["period"])

    return RecordBasedSeeker(**kwargs)

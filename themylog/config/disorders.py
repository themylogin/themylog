from __future__ import absolute_import

import isodate


from themylog.annotations.schedule import schedule
from themylog.annotations.title import title
from themylog.config.rules_tree import get_rules_tree
from themylog.config.scripts import find_scripts
from themylog.disorder.manager import DisorderManager
from themylog.disorder.seeker import *


def get_disorders(config, handlers):
    config_disorders = config.get("disorders", {})

    disorder_manager = DisorderManager(handlers)

    for seeker_config in config_disorders.get("seekers", []):
        cls = seeker_config["class"]
        del seeker_config["class"]

        key = seeker_config["title"]
        del seeker_config["title"]

        if cls == "expect_record":
            seeker = get_expect_record_disorder_seeker(**seeker_config)
        elif cls == "record_based":
            seeker = get_record_based_disorder_seeker(**seeker_config)
        else:
            raise NotImplementedError

        disorder_manager.add(key, seeker)

    script_disorders = find_scripts(config_disorders.get("directory"), {
        "schedule":     schedule,
        "title":        title,
    })

    return disorder_manager, script_disorders


def get_expect_record_disorder_seeker(**kwargs):
    kwargs["condition"] = get_rules_tree(kwargs["condition"])
    kwargs["interval"] = isodate.parse_duration(kwargs["interval"])

    return ExpectRecordSeeker(**kwargs)


def get_record_based_disorder_seeker(**kwargs):
    kwargs["right"] = get_rules_tree(kwargs["right"])
    kwargs["wrong"] = get_rules_tree(kwargs["wrong"])
    if "period" in kwargs:
        kwargs["period"] = isodate.parse_duration(kwargs["period"])

    return RecordBasedSeeker(**kwargs)

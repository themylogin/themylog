from collections import namedtuple
from datetime import datetime
import isodate
import operator
import os
import yaml

from themylog.level import levels
from themylog.feed import Feed
import themylog.receiver
import themylog.storage


class ConfigNotFound(Exception):
    pass


ReceiverEntity = namedtuple("ReceiverEntity", ["class_", "args"])
StorageEntity = namedtuple("StorageEntity", ["class_", "args"])


def find_config():
    configs = (os.path.expanduser("~/.config/themylog.yaml"), "/etc/themylog.yaml")

    for config in configs:
        if os.path.exists(config) and os.access(config, os.R_OK):
            return config

    raise ConfigNotFound("No readable config found. Places checked: %s" % configs)


def read_config(config):
    return yaml.load(open(config))


def get_receivers(config):
    return [ReceiverEntity(class_=d.keys()[0], args=d.values()[0]) for d in config["receivers"]]


def create_receivers(config):
    return [getattr(themylog.receiver, receiver.class_)(**receiver.args)
            for receiver in get_receivers(config)]


def get_storages(config):
    return [StorageEntity(class_=d.keys()[0], args=d.values()[0]) for d in config["storages"]]


def create_storages(config):
    return [getattr(themylog.storage, storage.class_)(**storage.args)
            for storage in get_storages(config)]


def get_feeds(config):
    return {feed: get_feed(rules) for feed, rules in config["feeds"].items()}


def get_cleanups(config):
    return [(isodate.parse_duration(cleanup["period"]), get_feed(cleanup["records"]))
            for cleanup in config.get("cleanup", [])]


def get_feed(rules):
    return Feed(get_rules_tree(rules))


def get_rules_tree(rules):
    if len(rules) == 0:
        return True
    else:
        conditions, action = parse_rule(rules[0])

        conditions_tree = get_conditions_tree(conditions.items())
        tail = get_rules_tree(rules[1:])

        if action == "accept":
            return (operator.or_, conditions_tree, tail)
        if action == "reject":
            return (operator.and_, (operator.not_, conditions_tree), tail)
        raise NotImplementedError


def parse_rule(rule):
    if "action" in rule:
        action = rule["action"].lower()
        if action in ["accept", "reject"]:
            conditions = dict(rule)
            del conditions["action"]
            return conditions, action
        else:
            raise Exception("Action should be either 'accept' or 'reject' not '%s'" % action)
    else:
        raise Exception("The following rule must contain action:\n%s" % yaml.dump(rule, default_flow_style=False))


def get_conditions_tree(conditions):
    if len(conditions) == 0:
        return True
    elif len(conditions) == 1:
        return get_condition_tree(*conditions[0])
    else:
        return (operator.and_, get_condition_tree(*conditions[0]), get_conditions_tree(conditions[1:]))


def get_condition_tree(key, value):
    field = lambda get_record_key: get_record_key(key)

    if isinstance(value, list):
        return condition_value_in(field, process_condition_value(key, value))
    else:
        op = operator.eq
        value = value.strip()
        for sym, sym_op in (("!=", operator.ne),
                            ("<=", operator.le),
                            (">=", operator.ge),
                            ("<", operator.lt),
                            (">", operator.gt)):
            if value.startswith(sym):
                op = sym_op
                value = yaml.load(value[len(sym):].strip())
                break

        if isinstance(value, list):
            if op == operator.ne:
                return (operator.not_, condition_value_in(field, process_condition_value(key, value)))
            else:
                raise ValueError("Lists do not support operator %s" % op.__name__)
        else:
            return (op, field, process_condition_value(key, value))


def process_condition_value(key, value):
    if isinstance(value, list):
        return [process_condition_value(key, v) for v in value]

    if key == "level":
        return levels[value]
    else:
        return value


def condition_value_in(field, value):
    if len(value) == 0:
        return False
    elif len(value) == 1:
        return (operator.eq, field, value[0])
    else:
        return (operator.or_, condition_value_in(field, [value[0]]), condition_value_in(field, value[1:]))

from collections import namedtuple
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
    return {feed: get_feed(description) for feed, description in config["feeds"].items()}

def get_feed(description):
    return Feed(get_feed_tree(*description.items()[0]))

def get_feed_tree(action, conditions):
    op = {"include": lambda x: x,
          "exclude": operator.not_}[action]

    return (op, get_feed_tree_conditions(conditions))

def get_feed_tree_conditions(conditions):
    if len(conditions) == 0:
        return False
    elif len(conditions) == 1:
        return get_feed_tree_condition(conditions[0].items())
    else:
        return (operator.or_, get_feed_tree_condition(conditions[0].items()), get_feed_tree_conditions(conditions[1:]))

def get_feed_tree_condition(condition):
    if len(condition) == 0:
        return True
    elif len(condition) == 1:
        return get_feed_tree_condition_part(*condition[0])
    else:
        return (operator.and_, get_feed_tree_condition_part(*condition[0]), get_feed_tree_condition(condition[1:]))

def get_feed_tree_condition_part(key, value):
    field = lambda get_record_key: get_record_key(key)

    if isinstance(value, list):
        return feed_field_in(field, process_feed_value(key, value))
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
                return (operator.not_, feed_field_in(field, process_feed_value(key, value)))
            else:
                raise ValueError("Lists do not support operator %s" % op.__name__)
        else:
            return (op, field, process_feed_value(key, value))


def process_feed_value(key, value):
    if isinstance(value, list):
        return [process_feed_value(key, v) for v in value]

    if key == "level":
        return levels[value]
    else:
        return value


def feed_field_in(field, value):
    if len(value) == 0:
        return False
    elif len(value) == 1:
        return (operator.eq, field, value[0])
    else:
        return (operator.or_, feed_field_in(field, [value[0]]), feed_field_in(field, value[1:]))

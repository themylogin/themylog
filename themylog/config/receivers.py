from collections import namedtuple

import themylog.receiver


ReceiverEntity = namedtuple("ReceiverEntity", ["class_", "args"])


def get_receivers(config):
    return [ReceiverEntity(class_=d.keys()[0], args=d.values()[0]) for d in config["receivers"]]


def create_receivers(config):
    return [getattr(themylog.receiver, receiver.class_)(**receiver.args)
            for receiver in get_receivers(config)]

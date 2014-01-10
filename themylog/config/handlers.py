from collections import namedtuple

import themylog.handler


HandlerEntity = namedtuple("HandlerEntity", ["class_", "args"])


def get_handlers(config):
    return [HandlerEntity(class_=d.keys()[0], args=d.values()[0]) for d in config["storages"]]


def create_handlers(config):
    return [getattr(themylog.handler, storage.class_)(**storage.args)
            for storage in get_handlers(config)]

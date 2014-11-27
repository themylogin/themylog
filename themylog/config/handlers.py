# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import namedtuple

import themylog.handler

__all__ = [b"HandlerEntity", b"get_handlers", b"list_handlers", b"create_handler", b"create_handlers"]


HandlerEntity = namedtuple("HandlerEntity", ["class_", "args"])


def get_handlers(config):
    return [HandlerEntity(class_=d.keys()[0], args=d.values()[0]) for d in config["handlers"]]


def list_handlers(config):
    return [(getattr(themylog.handler, handler.class_), handler.args)
            for handler in get_handlers(config)]


def create_handler(factory, args):
    return factory(**args)


def create_handlers(config):
    return [create_handler(factory, args) for factory, args in list_handlers(config)]

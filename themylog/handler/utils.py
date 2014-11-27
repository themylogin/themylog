# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from themylog.config.handlers import create_handler, list_handlers
from themylog.handler.interface import IRetrieveCapable


def get_retriever(config):
    for factory, args in list_handlers(config):
        if IRetrieveCapable.implementedBy(factory):
            return create_handler(factory, args)

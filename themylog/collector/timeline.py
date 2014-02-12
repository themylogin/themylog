# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import operator
import sys

from themylog.collector.collector import Collector
from themylog.config import find_config, read_config
from themylog.config.handlers import create_handlers
from themylog.handler.interface import IRetrieveCapable

__all__ = ["Timeline"]


class Timeline(Collector):
    def __init__(self, logger="root", msg_template="%s"):
        self.application = sys.argv[1]
        self.logger = logger
        self.msg_template = msg_template

        config = read_config(find_config())
        handlers = create_handlers(config)

        for handler in handlers:
            if IRetrieveCapable.providedBy(handler):
                self.retriever = handler
                break
        else:
            raise Exception("You should have at least one handler that is IRetrieveCapable to use Timeline collector")

    def contains(self, key):
        return len(self.retriever.retrieve((operator.and_,
                                               (operator.eq, lambda k: k("application"), self.application),
                                               (operator.and_,
                                                   (operator.eq, lambda k: k("logger"), self.logger),
                                                   (operator.eq, lambda k: k("msg"), self.msg_template % key))), 1)) > 0

    def store(self, key, args, **kwargs):
        kwargs["logger"] = self.logger
        self._log(self.msg_template % key, args, **kwargs)

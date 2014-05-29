# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import itertools
import operator
import sys

from themylog.client import Client
from themylog.config import find_config, read_config
from themylog.config.handlers import create_handlers
from themylog.config.processors import get_processors
from themylog.handler.interface import IRetrieveCapable
from themylog.processor import run_processor


if __name__ == "__main__":
    config = read_config(find_config())

    if sys.argv[1] == "run_processor":
        handlers = create_handlers(config)

        for handler in handlers:
            if IRetrieveCapable.providedBy(handler):
                retriever = handler
                break
        else:
            raise Exception("You should have at least one handler that is IRetrieveCapable to run processors")

        processors = get_processors(config)
        for processor in processors:
            if processor.name == sys.argv[2]:
                condition = True
                for k, v in itertools.izip_longest(*([iter(sys.argv[3:])] * 2)):
                    condition = (operator.and_, condition, (operator.eq, lambda _: _(k), v))

                client = Client()
                for record in reversed(retriever.retrieve(condition)):
                    for result in run_processor(processor, record):
                        client.log(result)
                break
        else:
            print "No processor '%s' exists" % sys.argv[2]

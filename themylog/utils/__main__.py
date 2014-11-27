# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import itertools
import operator
import sys

import themyutils.json

from themylog.analytics import get_analytics_kwargs
from themylog.client import Client
from themylog.config import find_config, read_config
from themylog.config.analytics import get_analytics
from themylog.config.processors import get_processors
from themylog.handler.utils import get_retriever
from themylog.processor import run_processor


if __name__ == "__main__":
    config = read_config(find_config())

    if sys.argv[1] == "run_analytics":
        retriever = get_retriever(config)

        analytics = get_analytics(config)
        if sys.argv[2] in analytics:
            analytics = analytics[sys.argv[2]]
            result = analytics.analyze(**get_analytics_kwargs(analytics, retriever))
            print(themyutils.json.dumps(result, ensure_ascii=False, indent=4))
        else:
            print("No analytics '%s' exists" % sys.argv[2])

    if sys.argv[1] == "run_processor":
        retriever = get_retriever(config)

        processors = get_processors(config)
        for processor in processors:
            if processor.name == sys.argv[2]:
                condition = True
                for k, v in itertools.izip_longest(*([iter(sys.argv[3:])] * 2)):
                    condition = (lambda k, v: (operator.and_, condition, (operator.eq, lambda _: _(k), v)))(k, v)

                client = Client()
                for record in reversed(retriever.retrieve(condition)):
                    for result in run_processor(processor, record):
                        client.log(result)
                break
        else:
            print("No processor '%s' exists" % sys.argv[2])

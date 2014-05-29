# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime

from themylog.level import levels
from themylog.record import Record


def run_processor(processor, record):
    try:
        result = processor.process(record)
    except Exception as e:
        return [Record(application=processor.name,
                       logger="root",
                       datetime=datetime.now(),
                       level=levels["error"],
                       msg="exception",
                       args={
                           "repr": repr(e)
                       },
                       explanation="")]

    if isinstance(result, Record):
        return [result]
    elif isinstance(result, list):
        return result
    else:
        return []

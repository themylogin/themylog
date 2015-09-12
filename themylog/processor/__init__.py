# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
import traceback

from themylog.level import levels
from themylog.record import Record


def run_processor(processor, record):
    try:
        result = processor.process(record)
    except Exception:
        return [Record(application="%s.processor" % processor.name,
                       logger="root",
                       datetime=datetime.now(),
                       level=levels["error"],
                       msg="exception",
                       args={
                           "record":    record,
                           "traceback": traceback.format_exc(),
                       },
                       explanation="")]

    if isinstance(result, Record):
        return [result]
    elif isinstance(result, list):
        return result
    else:
        return []

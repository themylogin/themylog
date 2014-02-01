# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import json
import sys


class TimeSeries(object):
    def __getattr__(self, attr):
        def logger(args, logger="root", level="info", explanation=""):
            sys.stdout.writelines([json.dumps({"logger":        logger,
                                               "level":         level,
                                               "msg":           attr,
                                               "args":          args,
                                               "explanation":   explanation,})])

        return logger

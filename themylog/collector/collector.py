# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import datetime as datetime_
import sys

import themylog.json


class Collector(object):
    def _log(self, msg, args, datetime=None, logger="root", level="info", explanation=""):
        if datetime is None:
            datetime = datetime_.datetime.now()

        sys.stdout.write("%s\n" % themylog.json.dumps({"datetime":     datetime,
                                                       "logger":       logger,
                                                       "level":        level,
                                                       "msg":          msg,
                                                       "args":         args,
                                                       "explanation":  explanation,}))

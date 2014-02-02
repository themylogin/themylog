# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import datetime
import isodate
import re
import json


class JSONDecoder(json.JSONDecoder):
    def decode(self, s):
        o = super(JSONDecoder, self).decode(s)
        o = self.traverse(o)
        return o

    def traverse(self, o):
        if isinstance(o, dict):
            return dict(map(lambda (k, v): (self.traverse(k), self.traverse(v)), o.iteritems()))

        if isinstance(o, list):
            return map(self.traverse, o)

        if isinstance(o, unicode):
            if re.match(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?", o):
                try:
                    return isodate.parse_datetime(o)
                except ValueError:
                    pass

        return o


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()

        try:
            return super(JSONEncoder, self).default(o)
        except TypeError:
            return repr(o)


def dumps(o):
    return JSONEncoder().encode(o)


def loads(s):
    return JSONDecoder().decode(s)

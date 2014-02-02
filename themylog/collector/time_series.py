# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from themylog.collector.collector import Collector


class TimeSeries(Collector):
    def __getattr__(self, attr):
        return lambda args, **kwargs: self._log(attr, args, **kwargs)

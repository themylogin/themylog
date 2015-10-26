# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import atexit
import copy
from datetime import datetime
import logging
import operator
import sys

from themylog.client import Client, Retriever
from themylog.record import Record

logger = logging.getLogger(__name__)

__all__ = [b"Storage"]


class Storage(object):
    def __init__(self):
        self.application = sys.argv[1]
        atexit.register(self.save)

        self.data = {}
        self.db_data = None

        records = Retriever().retrieve(
            (operator.and_,
             (operator.eq, lambda k: k("application"), "%s.collector" % self.application),
             (operator.eq, lambda k: k("logger"), "storage")),
            1)
        if len(records):
            self.data = records[0].args
            self.db_data = copy.deepcopy(self.data)

    def save(self):
        if self.data != self.db_data:
            Client().log(Record(datetime=datetime.now(),
                                application="%s.collector" % self.application,
                                logger="storage",
                                level=logging.INFO,
                                msg="data",
                                args=self.data,
                                explanation=""))

    def __contains__(self, item):
        return item in self.data

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        self.data[key] = value

    def get(self, *args, **kwargs):
        return self.data.get(*args, **kwargs)

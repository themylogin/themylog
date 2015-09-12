# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
import pika
from threading import Lock
from zope.interface import implements

from themylog.handler.base import BaseHandler
from themylog.record.serializer import serialize_json
from themylog.handler.interface import IHandler, IRequiresHeartbeat

__all__ = [b"AMQP"]

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)


class AMQP(BaseHandler):
    implements(IHandler, IRequiresHeartbeat)

    def __init__(self, exchange):
        self.exchange = exchange

        self.connection = None
        self.connection_lock = Lock()
        self.channel = None

        super(AMQP, self).__init__()

    def initialize(self):
        with self.connection_lock:
            self.connection = pika.BlockingConnection()

            self.channel = self.connection.channel()
            self.channel.exchange_declare(self.exchange, exchange_type="topic")

    def process(self, record):
        with self.connection_lock:
            self.channel.basic_publish(exchange=self.exchange,
                                       routing_key=("%s.%s.%s" % (record.application, record.logger, record.msg))[:128],
                                       body=serialize_json(record))

    def heartbeat(self):
        with self.connection_lock:
            try:
                self.connection.process_data_events()
            except Exception:
                logger.error("Exception when calling process_data_events")

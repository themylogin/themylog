from __future__ import absolute_import

import logging
import pika
from Queue import Queue
from threading import Thread
import time
from zope.interface import implements

from themylog.feed import IFeedsAware
from themylog.record.serializer import serialize_json
from themylog.storage.interface import IPersister

__all__ = ["AMQP"]

logger = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)


class AMQP(object):
    implements(IPersister, IFeedsAware)

    def __init__(self, exchange):
        self.exchange = exchange

        self.publish_queue = Queue()

    def set_feeds(self, feeds):
        self.feeds = feeds

        self.persister_thread = Thread(target=self._persister_thread)
        self.persister_thread.daemon = True
        self.persister_thread.start()

    def persist(self, record):
        routing_key = ("%s.%s.%s" % (record.application, record.logger, record.msg))[:128]
        body = serialize_json(record)

        self.publish_queue.put({
            "exchange": self.exchange,
            "routing_key": routing_key,
            "body": body,
        })

        for feed_name, feed in self.feeds.items():
            if feed.contains(record):
                self.publish_queue.put({
                    "exchange": "%s.%s" % (self.exchange, feed_name),
                    "routing_key": routing_key,
                    "body": body,
                })

    def _persister_thread(self):
        while True:
            try:
                connection = pika.BlockingConnection()

                channel = connection.channel()
                channel.exchange_declare(self.exchange, type="topic")
                for feed_name in self.feeds:
                    channel.exchange_declare("%s.%s" % (self.exchange, feed_name), type="topic")

                while True:
                    connection.process_data_events()

                    if not self.publish_queue.empty():
                        kwargs = self.publish_queue.get()
                        try:
                            channel.basic_publish(**kwargs)
                        except:
                            self.publish_queue.put(kwargs)
                            raise

                    time.sleep(0.01)

            except:
                logger.exception("An exception occurred in persister thread")
                time.sleep(5)

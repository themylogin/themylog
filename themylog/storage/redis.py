from __future__ import absolute_import

from redis import Redis
from zope.interface import implements

from themylog.storage.interface import IPersister

__all__ = ["RedisKeyIncrementer"]


class RedisKeyIncrementer(object):
    implements(IPersister)

    def __init__(self, key, pubsub_key):
        self.key = key
        self.pubsub_key = pubsub_key

        self.redis = Redis()
        self.redis.incr(self.key)

    def persist(self, record):
        self.redis.incr(self.key)
        self.redis.publish(self.pubsub_key, "")

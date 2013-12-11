from __future__ import absolute_import

import json
import logging
import operator
from Queue import Queue
from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import BigInteger, DateTime, Integer, PickleType, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import create_session
from threading import Thread
import time
from zope.interface import implements

from themylog.record import Record
from themylog.storage.interface import IPersister, IRetriever

__all__ = ["SQL"]

logger = logging.getLogger(__name__)

Base = declarative_base()


class SQLRecord(Base):
    __tablename__ = "log"

    id          = Column(BigInteger, primary_key=True)
    application = Column(String(length=255))
    logger      = Column(String(length=255))
    datetime    = Column(DateTime())
    level       = Column(Integer())
    msg         = Column(Text())
    args        = Column(PickleType(pickler=json))
    explanation = Column(Text())


class SQL(object):
    implements(IPersister, IRetriever)

    def __init__(self, dsn):
        self.dsn = dsn

        self.query_queue = Queue()

        self.persister_thread = Thread(target=self._persister_thread)
        self.persister_thread.daemon = True
        self.persister_thread.start()

        try:
            Base.metadata.create_all(create_engine(self.dsn))
        except:
            logger.exception("An exception occurred while issuing Base.metadata.create_all")

    def persist(self, record):
        self.query_queue.put(SQLRecord.__table__.insert().values(**record._asdict()))

    def retrieve(self, feed=None):
        query = self._create_session().query(SQLRecord)

        if feed:
            query = query.filter(feed.make_expr(lambda key: getattr(SQLRecord, key), {
                operator.not_: operator.inv,
            }))

        return [Record(**{k: getattr(record, k) for k in Record._fields})
                for record in query.\
                              order_by(SQLRecord.id.desc())
                              [:50]]

    def _persister_thread(self):
        while True:
            try:
                session = self._create_session()

                while True:
                    query = self.query_queue.get()
                    try:
                        session.execute(query)
                    except:
                        self.query_queue.put(query)
                        raise

            except:
                logger.exception("An exception occurred in persister thread")
                time.sleep(5)

    def _create_session(self):
        return create_session(create_engine(self.dsn))

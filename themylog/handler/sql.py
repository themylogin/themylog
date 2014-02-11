from __future__ import absolute_import

import logging
import operator
from Queue import Queue
from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import BigInteger, DateTime, Integer, PickleType, String, Text
from sqlalchemy import literal
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import create_session
from threading import Thread
import time
from zope.interface import implements

import themyutils.json

from themylog.rules_tree.evaluator import Evaluator
from themylog.record import Record
from themylog.handler.interface import IHandler, IRetrieveCapable, ICleanupCapable

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
    args        = Column(PickleType(pickler=themyutils.json))
    explanation = Column(Text())


class SQL(object):
    implements(IHandler, IRetrieveCapable, ICleanupCapable)

    def __init__(self, dsn):
        self.dsn = dsn

        self.query_queue = Queue()

        self.rules_tree_evaluator = Evaluator(
            lambda key: getattr(SQLRecord, key),
            constant_map={
                # Constant expressions such as (operator.not_, True) are evalauted in-place; however, as operator.not_
                # is substituted with operator.inv_, (operator.inv_, True) is -2. This is not what being expected.
                True: literal(True),
                False: literal(False),
            },
            operator_map={
                operator.not_: operator.inv,
            }
        )

        self.persister_thread = Thread(target=self._persister_thread)
        self.persister_thread.daemon = True
        self.persister_thread.start()

        try:
            Base.metadata.create_all(create_engine(self.dsn))
        except:
            logger.exception("An exception occurred while issuing Base.metadata.create_all")

    def handle(self, record):
        self.query_queue.put(SQLRecord.__table__.insert().values(**record._asdict()))

    def retrieve(self, rules_tree, limit):
        return [Record(**{k: getattr(record, k) for k in Record._fields})
                for record in self._create_query(rules_tree).\
                              order_by(SQLRecord.id.desc())
                              [:limit]]

    def cleanup(self, rules_tree, older_than):
        self._create_query(rules_tree).filter(SQLRecord.datetime < older_than).delete()

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

    def _create_query(self, rules_tree):
        query = self._create_session().query(SQLRecord)

        if rules_tree:
            query = query.filter(self.rules_tree_evaluator.eval(rules_tree))

        return query

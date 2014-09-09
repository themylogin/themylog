# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from itertools import combinations
import logging
import operator
from Queue import Queue
from sqlalchemy import create_engine
from sqlalchemy import Column, Index
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

__all__ = [b"SQL"]

logger = logging.getLogger(__name__)

Base = declarative_base()

index_columns = ["application", "logger", "datetime", "level", "msg"]


def index_name(index):
    return "_".join(index)


class SQLRecord(Base):
    __tablename__ = "log"

    id          = Column(BigInteger, primary_key=True)
    application = Column(String(length=255), nullable=False)
    logger      = Column(String(length=255), nullable=False)
    datetime    = Column(DateTime(), nullable=False)
    level       = Column(Integer(), nullable=False)
    msg         = Column(String(length=255), nullable=False)
    args        = Column(PickleType(pickler=themyutils.json), nullable=False)
    explanation = Column(Text(), nullable=False)

    __table_args__ = tuple(
        Index(index_name(index), *index)
        for index in set(
            sum(sum([[[combination, combination + ("datetime",)] if "datetime" not in combination else [combination]
                      for combination in combinations(index_columns, r + 1)]
                     for r in range(5)], []), [])
        )
    )


class SQL(object):
    implements(IHandler, IRetrieveCapable, ICleanupCapable)

    def __init__(self, dsn):
        self.dsn = dsn

        self.query_queue = Queue()

        self.rules_tree_evaluator = Evaluator(
            lambda key: getattr(SQLRecord, key),
            constant_map={
                # Constant expressions such as (operator.not_, True) are evaluated in-place; however, as operator.not_
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

    def retrieve(self, rules_tree, limit=None):
        records = self._create_query(rules_tree).order_by(SQLRecord.datetime.desc())
        if limit is not None:
            records = records[:limit]

        return map(lambda record: Record(**{k: getattr(record, k) for k in Record._fields}), records)

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

            index = self._build_index(rules_tree)
            if index:
                if "datetime" not in index:
                    index.append("datetime")
                query = query.with_hint(SQLRecord, "USE INDEX(%s)" % index_name(index))

        return query

    def _build_index(self, rules_tree):
        if rules_tree[0] == operator.or_:
            return None

        index = []
        for arg in rules_tree[1:]:
            if isinstance(arg, tuple):
                arg_index = self._build_index(arg)
                if arg_index:
                    for field in arg_index:
                        if field in index_columns and field not in index:
                            index.append(field)

            if callable(arg):
                arg(lambda field: index.append(field) if field in index_columns and field not in index else None)

        return index

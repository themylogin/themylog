# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from itertools import combinations
import logging
import operator
from sqlalchemy import create_engine
from sqlalchemy import Column, Index
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy import literal, literal_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import create_session
from zope.interface import implements

import themyutils.json

from themylog.rules_tree.evaluator import Evaluator
from themylog.record import Record
from themylog.handler.base import BaseHandler
from themylog.handler.interface import IHandler, IRetrieveCapable, ICleanupCapable

__all__ = [b"SQL"]

logger = logging.getLogger(__name__)

Base = declarative_base()

index_columns = ["application", "logger", "level", "msg"]


def index_name(index):
    return "_".join(index)


class SQLRecord(Base):
    __tablename__ = "log"

    id          = Column(Integer, primary_key=True)
    application = Column(Text(), nullable=False)
    logger      = Column(Text(), nullable=False)
    datetime    = Column(DateTime(), nullable=False)
    level       = Column(Integer(), nullable=False)
    msg         = Column(Text(), nullable=False)
    args        = Column(JSONB(), nullable=False)
    explanation = Column(Text(), nullable=False)

    __table_args__ = tuple(
        Index(index_name(index) + "_datetime", *(index + (literal_column("datetime desc"),)))
        for index in set(
            filter(
                lambda index: (not (("level" in index and "msg" in index))),
                sum([[combination
                      for combination in combinations(index_columns, r + 1)]
                     for r in range(len(index_columns))],
                    [])
            )
        )
    )


class SQL(BaseHandler):
    implements(IHandler, IRetrieveCapable, ICleanupCapable)

    def __init__(self, dsn):
        self.dsn = dsn

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

        try:
            Base.metadata.create_all(self._create_engine())
        except Exception:
            logger.error("An exception occurred while issuing Base.metadata.create_all", exc_info=True)

        super(SQL, self).__init__()

    def initialize(self):
        self.session = self._create_session()

    def process(self, record):
        self.session.execute(SQLRecord.__table__.insert().values(**record._asdict()))

    def retrieve(self, rules_tree, limit=None):
        records = self._create_query(rules_tree).order_by(SQLRecord.datetime.desc())
        if limit is not None:
            records = records[:limit]

        return map(lambda record: Record(**{k: getattr(record, k) for k in Record._fields}), records)

    def cleanup(self, rules_tree, older_than):
        self._create_query(rules_tree).filter(SQLRecord.datetime < older_than).delete(synchronize_session=False)

    def _create_engine(self):
        return create_engine(self.dsn,
                             json_serializer=themyutils.json.dumps,
                             json_deserializer=themyutils.json.loads)

    def _create_session(self):
        return create_session(self._create_engine())

    def _create_query(self, rules_tree):
        query = self._create_session().query(SQLRecord)

        if rules_tree:
            query = query.filter(self.rules_tree_evaluator.eval(rules_tree))

        return query

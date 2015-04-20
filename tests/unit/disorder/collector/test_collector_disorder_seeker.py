# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime, timedelta
from mock import MagicMock, Mock

from themylog.disorder.collector import CollectorDisorderSeeker
from themylog.level import levels
from ..seeker import DisorderSeekerAbstractTestCase


class CollectorDisorderTestCase(DisorderSeekerAbstractTestCase):
    def setUp(self):
        super(CollectorDisorderTestCase, self).setUp()

        collector = Mock()
        collector.name = "script"
        collector.annotations = {"allowed_downtime": timedelta(hours=1)}
        self.seeker = CollectorDisorderSeeker(collector)
        self.seeker.add_observer(self.observer, "test")

    def fake_good_record(self, **kwargs):
        record_kwargs = dict(datetime=datetime.now(),
                             application="script.collector",
                             logger="collector",
                             level=levels["info"])
        record_kwargs.update(**kwargs)
        return self.fake_record(**record_kwargs)

    def fake_bad_record(self, **kwargs):
        record_kwargs = dict(datetime=datetime.now(),
                             application="script.collector",
                             logger="collector",
                             level=levels["error"])
        record_kwargs.update(**kwargs)
        return self.fake_record(**record_kwargs)

    def test_regular_life(self):
        self.seeker.receive_record(self.fake_record(datetime=datetime.now(),
                                                    application="etc",
                                                    logger="misc",
                                                    level=levels["info"],
                                                    msg="nothing"))
        self.seeker.receive_record(self.fake_record(datetime=datetime.now(),
                                                    application="etc",
                                                    logger="misc",
                                                    level=levels["warning"],
                                                    msg="nothing yet"))
        self.assertEqual(len(self.observer.method_calls), 0)

    def test_there_is_no_disorder(self):
        self.seeker.receive_record(self.fake_good_record())
        self.assertEqual(len(self.observer.method_calls), 1)
        self.assertEqual(self.observer.there_is_no_disorder.called, True)

    def test_there_is_no_disorder_yet(self):
        self.seeker.receive_record(self.fake_bad_record())
        self.assertEqual(len(self.observer.method_calls), 0)

    def test_there_is_disorder(self):
        self.seeker.receive_record(self.fake_bad_record(datetime=datetime.now() - timedelta(hours=2)))
        self.assertEqual(len(self.observer.method_calls), 1)
        self.assertEqual(self.observer.there_is_disorder.called, True)

    def test_replay_not_functional(self):
        retriever = Mock()
        retriever.retrieve = MagicMock(return_value=[])

        self.seeker.replay(retriever)
        self.assertEqual(len(self.observer.method_calls), 1)
        self.assertEqual(self.observer.seeker_is_not_functional.called, True)

    def test_replay_there_is_no_disorder(self):
        retriever = Mock()
        retriever.retrieve = MagicMock(return_value=[self.fake_good_record()])

        self.seeker.replay(retriever)
        self.assertEqual(len(self.observer.method_calls), 1)
        self.assertEqual(self.observer.there_is_no_disorder.called, True)

    def test_replay_there_is_still_no_disorder(self):
        retriever = Mock()
        retriever.retrieve = MagicMock(return_value=[self.fake_bad_record(),
                                                     self.fake_bad_record(datetime=datetime.now() - timedelta(minutes=15)),
                                                     self.fake_good_record(datetime=datetime.now() - timedelta(minutes=30))])

        self.seeker.replay(retriever)
        self.assertEqual(self.observer.method_calls[-1][0], "there_is_no_disorder")

    def test_replay_there_was_disorder_but_now_there_is_not(self):
        retriever = Mock()
        retriever.retrieve = MagicMock(return_value=[self.fake_good_record(),
                                                     self.fake_bad_record(datetime=datetime.now() - timedelta(minutes=15))])

        self.seeker.replay(retriever)
        self.assertEqual(self.observer.method_calls[-1][0], "there_is_no_disorder")

    def test_replay_there_is_disorder(self):
        retriever = Mock()
        retriever.retrieve = MagicMock(return_value=[self.fake_bad_record(datetime=datetime.now() - timedelta(minutes=1)),
                                                     self.fake_bad_record(datetime=datetime.now() - timedelta(minutes=31)),
                                                     self.fake_bad_record(datetime=datetime.now() - timedelta(minutes=61)),
                                                     self.fake_good_record(datetime=datetime.now() - timedelta(minutes=91))])

        self.seeker.replay(retriever)
        self.assertEqual(self.observer.method_calls[-1][0], "there_is_disorder")

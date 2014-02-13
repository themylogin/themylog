from datetime import datetime
from mock import MagicMock, Mock
import operator
from testfixtures import Replacer
import textwrap
import unittest
import yaml

from themylog.config.disorders import get_record_based_disorder_seeker
from themylog.level import levels


class DisorderSeekerAbstractTestCase(unittest.TestCase):
    def setUp(self):
        self.observer = Mock()

    def create_seeker_from_yaml(self, disorder_yaml):
        seeker = get_record_based_disorder_seeker(**yaml.load(textwrap.dedent(disorder_yaml)))
        seeker.add_observer(self.observer, "ethernet")
        return seeker

    def fake_record(self, **kwargs):
        record = Mock()
        for k, v in kwargs.items():
            setattr(record, k, v)
        return record

    ethernet_yaml = """
        title: "Ethernet link is gigabit"
        right: [{application: ethernet_links, logger: server, msg: detected_gigabit_link, action: accept}]
        wrong: [{application: ethernet_links, logger: server, level: ">= warning", action: accept}]
        period: PT1H5M
    """


class ReceiveRecordTestCase(DisorderSeekerAbstractTestCase):
    def test_regular_life(self):
        seeker = self.create_seeker_from_yaml(self.ethernet_yaml)
        seeker.receive_record(self.fake_record(datetime=datetime.now(),
                                               application="smarthome",
                                               logger="bathroom_door",
                                               level=levels["info"],
                                               msg="opened"))
        seeker.receive_record(self.fake_record(datetime=datetime.now(),
                                               application="smarthome",
                                               logger="bathroom_door",
                                               level=levels["info"],
                                               msg="closed"))
        self.assertEqual(self.observer.there_is_disorder.called, False)
        self.assertEqual(self.observer.there_is_no_disorder.called, False)

    def test_has_disorder(self):
        seeker = self.create_seeker_from_yaml(self.ethernet_yaml)
        seeker.receive_record(self.fake_record(datetime=datetime.now(),
                                               application="smarthome",
                                               logger="bathroom_door",
                                               level=levels["info"],
                                               msg="opened"))
        seeker.receive_record(self.fake_record(datetime=datetime.now(),
                                               application="ethernet_links",
                                               logger="server",
                                               level=levels["error"],
                                               msg="f u"))
        seeker.receive_record(self.fake_record(datetime=datetime.now(),
                                               application="smarthome",
                                               logger="bathroom_door",
                                               level=levels["info"],
                                               msg="closed"))
        self.assertEqual(self.observer.there_is_disorder.called, True)
        self.assertEqual(self.observer.there_is_no_disorder.called, False)
        self.assertEqual(self.observer.method_calls[-1][0], "there_is_disorder")

    def test_has_no_disorder(self):
        seeker = self.create_seeker_from_yaml(self.ethernet_yaml)
        seeker.receive_record(self.fake_record(datetime=datetime.now(),
                                               application="smarthome",
                                               logger="bathroom_door",
                                               level=levels["info"],
                                               msg="opened"))
        seeker.receive_record(self.fake_record(datetime=datetime.now(),
                                               application="ethernet_links",
                                               logger="server",
                                               level=levels["info"],
                                               msg="detected_gigabit_link"))
        seeker.receive_record(self.fake_record(datetime=datetime.now(),
                                               application="smarthome",
                                               logger="bathroom_door",
                                               level=levels["info"],
                                               msg="closed"))
        self.assertEqual(self.observer.there_is_disorder.called, False)
        self.assertEqual(self.observer.there_is_no_disorder.called, True)
        self.assertEqual(self.observer.method_calls[-1][0], "there_is_no_disorder")

    def test_seeker_is_not_functional(self):
        seeker = self.create_seeker_from_yaml(self.ethernet_yaml)
        with Replacer() as r:
            d = datetime(2013, 1, 1, 0, 0, 0)
            r.replace("themylog.disorder.seeker.record_based.datetime", d)
            seeker.receive_record(self.fake_record(datetime=d,
                                                   application="smarthome",
                                                   logger="bathroom_door",
                                                   level=levels["info"],
                                                   msg="opened"))

            d = datetime(2013, 1, 1, 0, 0, 1)
            r.replace("themylog.disorder.seeker.record_based.datetime", d)
            seeker.receive_record(self.fake_record(datetime=d,
                                                   application="ethernet_links",
                                                   logger="server",
                                                   level=levels["info"],
                                                   msg="detected_gigabit_link"))
            self.assertEqual(self.observer.method_calls[-1][0], "there_is_no_disorder")

            d = datetime(2013, 1, 1, 1, 30, 0)
            r.replace("themylog.disorder.seeker.record_based.datetime", d)
            seeker.receive_record(self.fake_record(datetime=d,
                                                   application="smarthome",
                                                   logger="bathroom_door",
                                                   level=levels["info"],
                                                   msg="closed"))
            self.assertEqual(self.observer.method_calls[-1][0], "seeker_is_not_functional")


class ReplayTestCase(DisorderSeekerAbstractTestCase):
    def test_generated_condition(self):
        retriever = Mock()
        retriever.retrieve = MagicMock(return_value=[])

        seeker = self.create_seeker_from_yaml(self.ethernet_yaml)
        seeker.right = "right"
        seeker.wrong = "wrong"
        seeker.replay(retriever)

        retriever.retrieve.assert_called_with((operator.or_, "right", "wrong"), 1)

    def test_has_disorder(self):
        retriever = Mock()
        retriever.retrieve = MagicMock(return_value=[self.fake_record(datetime=datetime.now(),
                                                                      application="ethernet_links",
                                                                      logger="server",
                                                                      level=levels["error"],
                                                                      msg="f u")])

        seeker = self.create_seeker_from_yaml(self.ethernet_yaml)
        seeker.replay(retriever)

        self.assertEqual(self.observer.there_is_disorder.called, True)
        self.assertEqual(self.observer.there_is_no_disorder.called, False)
        self.assertEqual(self.observer.method_calls[-1][0], "there_is_disorder")

    def test_has_no_disorder(self):
        retriever = Mock()
        retriever.retrieve = MagicMock(return_value=[self.fake_record(datetime=datetime.now(),
                                                                      application="ethernet_links",
                                                                      logger="server",
                                                                      level=levels["info"],
                                                                      msg="detected_gigabit_link")])

        seeker = self.create_seeker_from_yaml(self.ethernet_yaml)
        seeker.replay(retriever)

        self.assertEqual(self.observer.there_is_disorder.called, False)
        self.assertEqual(self.observer.there_is_no_disorder.called, True)
        self.assertEqual(self.observer.method_calls[-1][0], "there_is_no_disorder")

    def test_seeker_is_not_functional(self):
        retriever = Mock()
        retriever.retrieve = MagicMock(return_value=[])

        seeker = self.create_seeker_from_yaml(self.ethernet_yaml)
        seeker.replay(retriever)

        self.assertEqual(self.observer.method_calls[-1][0], "seeker_is_not_functional")

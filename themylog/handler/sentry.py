# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import json
import logging
from raven import Client
import requests
from requests.auth import HTTPBasicAuth
from zope.interface import implements

from themylog.config.rules_tree import get_rules_tree
from themylog.handler.base import BaseHandler
from themylog.handler.interface import IHandler
from themylog.rules_tree import match_record

__all__ = [b"Sentry"]


logger = logging.getLogger(__name__)


class Sentry(BaseHandler):
    implements(IHandler)

    def __init__(self, url, organization, team, key, rules_tree):
        self.url = url
        self.organization = organization
        self.team = team
        self.auth = HTTPBasicAuth(key, "")
        self.rules_tree = get_rules_tree(rules_tree)

        self.dsns = {}

        super(Sentry, self).__init__()

    def initialize(self):
        pass

    def process(self, record):
        if match_record(self.rules_tree, record):
            dsn = self.dsns.get(record.application)
            if dsn is None:
                projects = requests.get("%s/api/0/projects/" % self.url,
                                        auth=self.auth).json()
                for project in projects:
                    if project["name"] == record.application:
                        break
                else:
                    project = requests.post("%s/api/0/teams/%s/%s/projects/" % (self.url,
                                                                                self.organization,
                                                                                self.team),
                                            auth=self.auth,
                                            headers={"Content-type": "application/json"},
                                            data=json.dumps({"name": record.application})).json()

                for key in requests.get("%s/api/0/projects/%s/%s/keys/" % (self.url,
                                                                           self.organization,
                                                                           project["slug"]),
                                        auth=self.auth).json():
                    dsn = key["dsn"]["secret"]
                    self.dsns[record.application] = dsn

            client = Client(dsn, raise_send_errors=True)
            client.capture("raven.events.Message",
                           message=record.msg,
                           formatted=record.explanation or record.msg,
                           data={"logger": record.logger},
                           date=record.datetime,
                           extra=record._asdict())

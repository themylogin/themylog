# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from django.conf import settings
from django.db import connection
import logging
import os
from raven import Client
from zope.interface import implements

from themylog.config.rules_tree import get_rules_tree
from themylog.handler.base import BaseHandler
from themylog.handler.interface import IHandler
from themylog.rules_tree import match_record

__all__ = [b"Sentry"]


logger = logging.getLogger(__name__)


class Sentry(BaseHandler):
    implements(IHandler)

    def __init__(self, team, organization, rules_tree):
        config_file = os.path.expanduser("~/.sentry/sentry.conf.py")
        config = {b"__file__": config_file}
        execfile(config_file, config)
        cfg = {k: v for k, v in config.iteritems()
               if k in ["DATABASES"] or any(k.startswith("%s_" % s)
                                            for s in ["AUTH", "CACHE", "SENTRY"])}
        cfg["LOGGING"] = {"version": 1,
                          "disable_existing_loggers": False}
        settings.configure(**cfg)

        from sentry.models import Team, Project, Organization
        self.Project = Project

        self.team = Team.objects.get(name=team)
        self.organization = Organization.objects.get(name=organization)
        self.projects = {}

        self.rules_tree = get_rules_tree(rules_tree)

        super(Sentry, self).__init__()

    def initialize(self):
        if connection.connection:
            try:
                connection.connection.close()
            except Exception:
                logger.info("Unable to close connection", exc_info=True)

        try:
            connection.connection = None
        except Exception:
            logger.info("Unable to set connection to None", exc_info=True)

    def process(self, record):
        if match_record(self.rules_tree, record):
            dsn = self.projects.get(record.application)
            if dsn is None:
                project = self.Project.objects.get_or_create(team=self.team, organization=self.organization,
                                                             name=record.application)[0]
                dsn = project.key_set.get_or_create()[0].get_dsn()
                self.projects[record.application] = dsn

            client = Client(dsn, raise_send_errors=True)
            client.capture("raven.events.Message",
                           message=record.msg,
                           formatted=record.explanation or record.msg,
                           data={"logger": record.logger},
                           date=record.datetime,
                           extra=record._asdict())

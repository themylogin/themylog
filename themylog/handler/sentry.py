# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from django.conf import settings
from django.db import connection
import logging
import os
from Queue import Queue
from raven import Client
from threading import Thread
import time
from zope.interface import implements

from themylog.config.rules_tree import get_rules_tree
from themylog.handler.interface import IHandler
from themylog.rules_tree import match_record

__all__ = [b"Sentry"]


logger = logging.getLogger(__name__)


class Sentry(object):
    implements(IHandler)

    def __init__(self, team, organization, owner, rules_tree):
        config_file = os.path.expanduser("~/.sentry/sentry.conf.py")
        config = {b"__file__": config_file}
        execfile(config_file, config)
        settings.configure(**{k: v for k, v in config.iteritems()
                              if k in ["DATABASES"] or any(k.startswith("%s_" % s)
                                                           for s in ["AUTH", "SENTRY"])})

        from sentry.models import Team, Project, ProjectKey, Organization, User
        self.Project = Project
        self.ProjectKey = ProjectKey

        self.team = Team.objects.get(name=team)
        self.organization = Organization.objects.get(name=organization)
        self.owner = User.objects.get(username=owner)
        self.projects = {}

        self.rules_tree = get_rules_tree(rules_tree)

        self.publish_queue = Queue()

        self.persister_thread = Thread(target=self._persister_thread)
        self.persister_thread.daemon = True
        self.persister_thread.start()

    def handle(self, record):
        if match_record(self.rules_tree, record):
            self.publish_queue.put(record)

    def _persister_thread(self):
        while True:
            try:
                while True:
                    record = self.publish_queue.get()
                    try:
                        dsn = self.projects.get(record.application)
                        if dsn is None:
                            project = self.Project.objects.get_or_create(team=self.team, organization=self.organization,
                                                                         name=record.application)[0]
                            dsn = project.key_set.get_or_create(user=self.owner)[0].get_dsn()
                            self.projects[record.application] = dsn

                        client = Client(dsn)
                        client.capture("raven.events.Message",
                                       message=record.msg,
                                       formatted=record.explanation or record.msg,
                                       data={"logger": record.logger},
                                       date=record.datetime,
                                       extra=record._asdict())
                    except Exception:
                        self.publish_queue.put(record)
                        raise

            except Exception:
                logger.error("An exception occurred in persister thread", exc_info=True)

                try:
                    connection.connection.close()
                except Exception:
                    logger.info("Unable to close connection", exc_info=True)

                try:
                    connection.connection = None
                except Exception:
                    logger.info("Unable to set connection to None", exc_info=True)

                time.sleep(5)

# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import defaultdict
import copy
import fcntl
import logging
import os
import subprocess
import tempfile
import threading
import time
from tl.testing.thread import ThreadAwareTestCase
import yaml

from themylog.client import Client

logger = logging.getLogger(__name__)


class IntegrationTestCase(ThreadAwareTestCase):
    def setUp(self):
        self.unix_socket_path = None
        self.unix_socket = None
        self.sqlite_database_path = None
        self.celerybeat_schedule_path = None
        self.config_file = None
        self.processes = []

        self.client = None
        self.expects = defaultdict(threading.Event)

    def tearDown(self):
        for process in self.processes:
            process.poll()
            if process.returncode is None:
                process.terminate()
                process.wait()

        os.unlink(self.sqlite_database_path)
        os.unlink(self.celerybeat_schedule_path)

        os.unlink(self.unix_socket_path)

    def start(self, config=None):
        if config is None:
            config = {}
        config = copy.deepcopy(config)

        if "receivers" not in config:
            fh, self.unix_socket_path = tempfile.mkstemp()
            os.unlink(self.unix_socket_path)

            config["receivers"] = [{"UnixServer": {"path": self.unix_socket_path}}]

        if "handlers" not in config:
            fh, self.sqlite_database_path = tempfile.mkstemp()
            config["handlers"] = [{"SQL": {"dsn": "sqlite:///%s" % self.sqlite_database_path}}]

        if "celery" not in config:
            fh, self.celerybeat_schedule_path = tempfile.mkstemp()
            os.unlink(self.celerybeat_schedule_path)
            config["celery"] = {"BROKER_URL": "sqla+sqlite://",
                                "CELERYBEAT_SCHEDULE_FILENAME": self.celerybeat_schedule_path}

        fh, self.config_file = tempfile.mkstemp()
        with open(self.config_file, "w") as f:
            yaml.safe_dump(config, f)

        self.client = Client(self.config_file)

        start_at = time.time()
        p = subprocess.Popen(["python", "-m", "themylog", "-c", self.config_file, "-l", "debug"],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        fd = p.stdout.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        lines = []
        while time.time() - start_at < 10:
            p.poll()
            if p.returncode is not None:
                lines += p.communicate()[0]
                self.fail("themylog process terminated with exit code = %d:\n%s" % (p.returncode,
                                                                                    "\n".join(lines)))
            try:
                line = p.stdout.readline().rstrip()
            except IOError:
                time.sleep(0.001)
            else:
                lines.append(line)
                if line.endswith(" INFO/MainProcess] Running"):
                    self.processes.append(p)
                    self.start_thread(self._read_from_themylog, p, lines)
                    return

        self.fail("themylog process did not start:\n%s" % "\n".join(lines))

    def start_thread(self, target, *args, **kwargs):
        self.run_in_thread(lambda: target(*args, **kwargs))

    def expect(self, text, timeout=5):
        event = self.expects[text]
        if event.wait(timeout) is not True:
            self.fail("Couldn't wait to read '%s' from themylog" % text)
        else:
            event.clear()

    def log_and_wait(self, record):
        self.client.log(record)
        self.expect(" DEBUG/MainProcess] Processing record")

    def _read_from_themylog(self, p, lines):
        while True:
            p.poll()
            if p.returncode is not None:
                if p.returncode <= 0:
                    return

                lines.append(p.communicate()[0])
                self.fail("themylog process terminated with exit code = %d:\n%s" % (p.returncode,
                                                                                    "\n".join(lines)))

            try:
                line = p.stdout.readline().rstrip()
            except IOError:
                continue

            lines.append(line)
            for expect, event in self.expects.iteritems():
                if expect in line:
                    event.set()

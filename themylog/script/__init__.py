# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import namedtuple
from datetime import datetime
import logging
import subprocess
import sys
from threading import Thread

from themyutils.subprocess import preexec_fn

logger = logging.getLogger(__name__)

__all__ = [b"TooFrequentException", b"TimeoutException", b"Script"]

ScriptResult = namedtuple("ScriptResult", ["returncode", "stdout", "stderr"])


class TooFrequentException(Exception):
    pass


class TimeoutException(Exception):
    pass


class Script(object):
    def __init__(self, path, name, annotations):
        self.path = path
        self.name = name
        self.annotations = annotations

        self.last_run = datetime.min

    def run(self, force=False):
        if "schedule" in self.annotations:
            if not self.annotations["schedule"].is_due(self.last_run)[0]:
                raise TooFrequentException

        self.last_run = datetime.utcnow()

        p = subprocess.Popen([sys.executable, self.path, self.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             preexec_fn=preexec_fn)
        stdout_stderr = []

        def target():
            stdout_stderr[:] = p.communicate()

        thread = Thread(target=target)
        thread.start()

        thread.join(self.annotations.get("timeout", 60))
        if not thread.is_alive():
            return ScriptResult(p.returncode, stdout_stderr[0], stdout_stderr[1])
        else:
            p.terminate()
            thread.join()
            raise TimeoutException()

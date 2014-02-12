# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
import subprocess
import sys

import themyutils.json

from themylog.client import Client
from themylog.level import levels
from themylog.record import Record


def setup_collectors(celery, collectors):
    for collector in collectors:
        client = Client()

        collector_task = celery.task(create_collector_task(client, collector.path, collector.name),
                                     name="collectors.%s" % collector.name)

        celery.conf.CELERYBEAT_SCHEDULE[collector_task.name] = {
            "task":     collector_task.name,
            "schedule": collector.annotations["schedule"],
        }


def create_collector_task(client, path, name):
    def collector_task():
        p = subprocess.Popen([sys.executable, path, name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()

        records = []
        if p.returncode == 0:
            stdout = stdout.strip()
            if stdout:
                for data in map(themyutils.json.loads, stdout.split("\n")):
                    records.append(Record(datetime=data["datetime"],
                                          application=name,
                                          logger=data["logger"],
                                          level=levels[data["level"]],
                                          msg=data["msg"],
                                          args=data["args"],
                                          explanation=data["explanation"]))
        else:
            records.append(Record(datetime=datetime.now(),
                                  application=name,
                                  logger="root",
                                  level=levels["error"],
                                  msg="nonzero_exit_code",
                                  args={
                                      "code": p.returncode,
                                      "stdout": stdout,
                                      "stderr": stderr,
                                  },
                                  explanation=""))

        for record in records:
            client.log(record)

    return collector_task

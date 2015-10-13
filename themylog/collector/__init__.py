# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
import subprocess
import sys
from threading import Thread

import themyutils.json

from themylog.client import Client
from themylog.level import levels
from themylog.record import Record


def setup_collectors(celery, collectors):
    for collector in collectors:
        client = Client()

        collector_task = celery.task(create_collector_task(collector, client), name="collectors.%s" % collector.name)

        celery.conf.CELERYBEAT_SCHEDULE[collector_task.name] = {
            "task":     collector_task.name,
            "schedule": collector.annotations["schedule"],
        }


def create_collector_task(collector, client):
    def collector_task():
        records = []

        p = subprocess.Popen([sys.executable, collector.path, collector.name],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_stderr = []

        def target():
            stdout_stderr[:] = p.communicate()

        thread = Thread(target=target)
        thread.start()

        thread.join(collector.annotations.get("timeout", 60))
        if not thread.is_alive():
            if p.returncode == 0 or not collector.annotations.get("transactional", False):
                stdout = stdout_stderr[0].strip()
                if stdout:
                    for data in stdout.split("\n"):
                        try:
                            data = themyutils.json.loads(data)
                        except Exception:
                            pass
                        else:
                            records.append(Record(datetime=data["datetime"],
                                                  application=collector.name,
                                                  logger=data["logger"],
                                                  level=levels[data["level"]],
                                                  msg=data["msg"],
                                                  args=data["args"],
                                                  explanation=data["explanation"]))

            if p.returncode == 0:
                records.append(Record(datetime=datetime.now(),
                                      application="%s.collector" % collector.name,
                                      logger="collector",
                                      level=levels["info"],
                                      msg="completed_successfully",
                                      args={},
                                      explanation=""))
            else:
                records.append(Record(datetime=datetime.now(),
                                      application="%s.collector" % collector.name,
                                      logger="collector",
                                      level=levels["error"],
                                      msg="nonzero_exit_code",
                                      args={
                                          "code": p.returncode,
                                          "stdout": stdout_stderr[0],
                                          "stderr": stdout_stderr[1],
                                      },
                                      explanation=""))
        else:
            p.terminate()
            thread.join()
            records.append(Record(datetime=datetime.now(),
                                  application="%s.collector" % collector.name,
                                  logger="collector",
                                  level=levels["error"],
                                  msg="timeout",
                                  args={},
                                  explanation=""))

        for record in sorted(records, key=lambda record: record.datetime):
            client.log(record)

    return collector_task

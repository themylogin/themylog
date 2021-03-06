# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
import operator
import sys

import themyutils.json

from themylog.client import Client
from themylog.disorder.seeker.record_based import RecordBasedSeeker
from themylog.level import levels
from themylog.record import Record
from themylog.script import TimeoutException


class Disorder(object):
    def __init__(self, key=None):
        self.key = key

    def ok(self, explanation, **kwargs):
        self.state(True, explanation, **kwargs)

    def fail(self, explanation, **kwargs):
        self.state(False, explanation, **kwargs)

    def exception(self, explanation, **kwargs):
        self.state(False, explanation, **dict(kwargs, exc_info=sys.exc_info()))

    def state(self, ok, explanation, **kwargs):
        self.log(ok, kwargs, explanation)

    def log(self, ok, args, explanation):
        sys.stdout.write(b"%s\n" % themyutils.json.dumps({"key":         self.key,
                                                          "ok":          ok,
                                                          "args":        args,
                                                          "explanation": explanation}))


def setup_script_disorder_seekers(disorder_manager, celery, script_disorders):
    for script in script_disorders:
        disorder_manager.add(script.annotations["title"],
                             create_script_disorder_seeker(script.name))

        client = Client()

        script_task = celery.task(create_script_disorder_seeker_task(script, client),
                                  name="script_disorder_seeker.%s" % script.name)

        celery.conf.CELERYBEAT_SCHEDULE[script_task.name] = {
            "task":     script_task.name,
            "schedule": script.annotations["schedule"],
        }


class ScriptSeeker(RecordBasedSeeker):
    def disorder_reason(self, record):
        if record.msg == "disorder_checker_returned_nonzero_exit_code":
            return ("Скрипт вернул код %d:\n%s%s" % (record.args["code"],
                                                     (record.args["stdout"] + "\n").strip(),
                                                     (record.args["stderr"] + "\n").strip())).strip()
        elif record.msg == "disorder_checker_returned_nothing":
            return "Скрипт не вернул ничего"
        else:
            return [{"is_disorder": not potential_disorder["ok"],
                     "disorder": {"datetime": record.datetime,
                                  "reason": potential_disorder["explanation"],
                                  "data": potential_disorder["args"]},
                     "title": potential_disorder["key"]}
                    for potential_disorder in record.args]


def create_script_disorder_seeker(name):
    return ScriptSeeker(
        right=(operator.and_,
                  (operator.eq, lambda k: k("application"), name),
                  (operator.and_,
                      (operator.eq, lambda k: k("logger"), "script_disorder_checker"),
                      (operator.eq, lambda k: k("msg"), "disorder_checked"))),
        wrong=(operator.and_,
                  (operator.eq, lambda k: k("application"), name),
                  (operator.and_,
                      (operator.eq, lambda k: k("logger"), "script_disorder_checker"),
                      (operator.ne, lambda k: k("msg"), "disorder_checked")))
    )


def create_script_disorder_seeker_task(script, client):
    def script_disorder_task(*args, **kwargs):
        try:
            result = script.run(*args, **kwargs)
        except TimeoutException:
            level = "error"
            msg = "disorder_checker_timeout"
            args = {}
        else:
            if result.returncode == 0:
                stdout = result.stdout.strip()
                if stdout:
                    disorders = map(themyutils.json.loads, stdout.split("\n"))

                    if any(not disorder["ok"] for disorder in disorders):
                        level = "warning"
                        msg = "disorder_found"
                    else:
                        level = "info"
                        msg = "disorder_checked"
                    args = disorders
                else:
                    level = "error"
                    msg = "disorder_checker_returned_nothing"
                    args = {}
            else:
                level = "error"
                msg = "disorder_checker_returned_nonzero_exit_code"
                args = {
                    "code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

        client.log(Record(datetime=datetime.now(),
                          application=script.name,
                          logger="script_disorder_checker",
                          level=levels[level],
                          msg=msg,
                          args=args,
                          explanation=""))

    return script_disorder_task

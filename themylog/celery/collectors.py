# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals
import ast
from celery.schedules import crontab
from datetime import datetime
import os
import subprocess
import sys

import themyutils.json

from themylog.client import Client
from themylog.level import levels
from themylog.record import Record


def setup_collectors(celery, config):
    collectors = config.get("collectors")
    if collectors:
        client = Client()

        for collector in os.listdir(collectors["directory"]):
            path = os.path.join(collectors["directory"], collector)
            name, ext = os.path.splitext(collector)

            if ext != ".py":
                continue

            annotations = read_annotations(open(path).read().decode("utf-8"))
            collector_task = celery.task(create_collector_task(client, path, name), name="collectors.%s" % name)

            celery.conf.CELERYBEAT_SCHEDULE[collector_task.name] = {
                "task":     collector_task.name,
                "schedule": annotations["schedule"],
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


def read_annotations(code):
    annotations = {}

    for line in code.split("\n"):
        if not line.startswith("#"):
            break

        try:
            tree = ast.parse(line.lstrip("# "))
        except:
            continue

        x = create_schedule(tree)
        if x:
            annotations["schedule"] = x

    return annotations


def create_schedule(tree):
    if (isinstance(tree, ast.Module) and len(tree.body) > 0 and
        isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Call) and
        isinstance(tree.body[0].value.func, ast.Name) and tree.body[0].value.func.id == "crontab"):

        kwargs = {}
        for keyword in tree.body[0].value.keywords:
            if isinstance(keyword.value, ast.Num):
                value = keyword.value.n
            elif isinstance(keyword.value, ast.Str):
                value = keyword.value.s
            else:
                raise Exception("Unknown keyword argument value type: %r" % keyword.value)

            kwargs[keyword.arg] = value

        return crontab(**kwargs)

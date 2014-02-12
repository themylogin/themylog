# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import ast
from celery.schedules import crontab


def schedule(tree):
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

# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import ast

from themylog.annotations import NoneValue


def timeout(tree):
    if (isinstance(tree, ast.Module) and len(tree.body) > 0 and
        isinstance(tree.body[0], ast.Assign) and
        isinstance(tree.body[0].targets[0], ast.Name) and
        tree.body[0].targets[0].id == "timeout"):
        if isinstance(tree.body[0].value, ast.Num):
            return tree.body[0].value.n
        if isinstance(tree.body[0].value, ast.Name) and tree.body[0].value.id == "None":
            return NoneValue

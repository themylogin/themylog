# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import ast


def title(tree):
    if (isinstance(tree, ast.Module) and len(tree.body) > 0 and
        isinstance(tree.body[0], ast.Assign) and
        isinstance(tree.body[0].targets[0], ast.Name) and tree.body[0].targets[0].id == "title" and
        isinstance(tree.body[0].value, ast.Str)):
        return tree.body[0].value.s.decode("utf-8")

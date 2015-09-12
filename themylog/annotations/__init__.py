# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import ast


class NoneValue(object):
    pass


def function_annotation(tree, name, function):
    if (isinstance(tree, ast.Module) and len(tree.body) > 0 and
        isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Call) and
        isinstance(tree.body[0].value.func, ast.Name) and tree.body[0].value.func.id == name):

        kwargs = {}
        for keyword in tree.body[0].value.keywords:
            kwargs[keyword.arg] = _ast_value(keyword.value)

        return function(**kwargs)


def value_annotation(tree, name, type):
    if (isinstance(tree, ast.Module) and len(tree.body) > 0 and
        isinstance(tree.body[0], ast.Assign) and
        isinstance(tree.body[0].targets[0], ast.Name) and tree.body[0].targets[0].id == name):
        if isinstance(tree.body[0].value, type):
            return _ast_value(tree.body[0].value)
        if isinstance(tree.body[0].value, ast.Name) and tree.body[0].value.id == "None":
            return NoneValue


def _ast_value(value):
    if isinstance(value, ast.Num):
        return value.n
    elif isinstance(value, ast.Str):
        return value.s.decode("utf-8")
    else:
        raise Exception("Unknown AST value type: %r" % value)



def read_annotations(code, annotation_parsers):
    annotations = {}

    for line in code.split("\n"):
        if not line.startswith("#"):
            break

        try:
            tree = ast.parse(line.lstrip("# "))
        except Exception:
            continue

        for key, parser in annotation_parsers.items():
            annotation = parser(tree)
            if annotation:
                if annotation == NoneValue:
                    annotation = None
                annotations[key] = annotation
                break

    return annotations

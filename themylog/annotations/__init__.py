# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import ast


class NoneValue(object):
    pass


def read_annotations(code, annotation_parsers):
    annotations = {}

    for line in code.split("\n"):
        if not line.startswith("#"):
            break

        try:
            tree = ast.parse(line.lstrip("# "))
        except:
            continue

        for key, parser in annotation_parsers.items():
            annotation = parser(tree)
            if annotation:
                if annotation == NoneValue:
                    annotation = None
                annotations[key] = annotation
                break

    return annotations

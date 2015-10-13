# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import ast

from themylog.annotations import value_annotation


def transactional(tree):
    return value_annotation(tree, "transactional", ast.Num)

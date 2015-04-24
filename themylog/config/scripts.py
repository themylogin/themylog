# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import namedtuple
import os

from themylog.annotations import read_annotations

Script = namedtuple("Collector", ["name", "path", "annotations"])


def find_scripts(directory, annotation_parsers):
    scripts = []
    if directory:
        for script in os.listdir(directory):
            path = os.path.join(directory, script)
            name, ext = os.path.splitext(script)
            name = name.rstrip("_")

            if ext != ".py":
                continue

            annotations = read_annotations(open(path).read().decode("utf-8"), annotation_parsers)

            scripts.append(Script(name=name, path=path, annotations=annotations))

    return scripts

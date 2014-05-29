# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import namedtuple
import sys

from themylog.config.scripts import find_scripts

Processor = namedtuple("Processor", ["name", "process"])


def get_processors(config):
    processors = []
    directory = config.get("processors", {}).get("directory")
    if directory:
        sys.path.insert(0, directory)
        for script in find_scripts(directory, {}):
            processors.append(Processor(name=script.name,
                                        process=__import__(script.name).process))
    return processors

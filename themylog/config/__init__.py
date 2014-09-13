# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import os
import yaml


class ConfigNotFound(Exception):
    pass


def find_config():
    configs = (os.path.expanduser("~/.config/themylog.yaml"), "/etc/themylog.yaml")

    for config in configs:
        if os.path.exists(config) and os.access(config, os.R_OK):
            return config

    raise ConfigNotFound("No readable config found. Places checked: %s" % (configs,))


def read_config(config):
    return yaml.load(open(config))

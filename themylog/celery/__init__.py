# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from celery import Celery
import logging

from themylog.celery.cleanup import setup_cleanup
from themylog.celery.collectors import setup_collectors
from themylog.config import find_config, read_config

logging.basicConfig(level=logging.DEBUG)

config = read_config(find_config())

celery = Celery()
celery.config_from_object(config["celery"])

setup_cleanup(celery, config)
setup_collectors(celery, config)

# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import argparse
from celery import Celery
from celery.app.defaults import DEFAULT_PROCESS_LOG_FMT
from collections import defaultdict
import functools
import itertools
import logging
import os
import sys
import time

from themyutils.argparse import LoggingLevelType
from themyutils.threading import start_daemon_thread

from themylog.cleanup import setup_cleanup
from themylog.collector import setup_collectors
from themylog.config import find_config, read_config
from themylog.config.analytics import get_analytics
from themylog.config.cleanup import get_cleanups
from themylog.config.collectors import get_collectors
from themylog.config.disorders import get_disorders
from themylog.config.feeds import get_feeds
from themylog.config.handlers import create_handlers
from themylog.config.processors import get_processors
from themylog.config.receivers import create_receivers
from themylog.disorder.collector import setup_collector_disorder_seekers
from themylog.disorder.internal import setup_internal_disorder_seekers
from themylog.disorder.script import setup_script_disorder_seekers
from themylog.feed import IFeedsAware
from themylog.handler.manager import HandlerManager
from themylog.processor.handler import ProcessorRunner
from themylog.queue.fanout import Fanout
from themylog.queue.persistent_queue import PersistentQueue
from themylog.web_server import setup_web_server


def create_persistent_queue(name):
    path = os.path.join(os.path.expanduser("~/.local/themylog"), "queues", name)
    if not os.path.exists(path):
        os.makedirs(path)

    return PersistentQueue(path)


def receiver_thread(receiver, record_fanout):
    for record in receiver.receive():
        record_fanout.put(record)


def heartbeat_thread(heartbeats):
    while True:
        for heartbeat in heartbeats:
            heartbeat.heartbeat()

        time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config")
    parser.add_argument("-l", "--level", type=LoggingLevelType, default=logging.INFO)
    args = parser.parse_args(sys.argv[1:])

    logging.basicConfig(level=args.level, format=DEFAULT_PROCESS_LOG_FMT)
    logger = logging.getLogger(__name__)

    config = read_config(args.config or find_config())

    record_fanout = Fanout()
    handler_manager = HandlerManager(record_fanout, create_persistent_queue)

    logger.info("Creating receivers")

    receivers = create_receivers(config)

    for receiver in receivers:
        start_daemon_thread(functools.partial(receiver_thread, receiver, record_fanout))

    logger.info("Creating handlers")

    handlers = create_handlers(config)

    handlers_name_counters = defaultdict(lambda: itertools.count(1))
    for handler in handlers:
        name = "handler-%s-%d" % (handler.__class__.__name__, handlers_name_counters[handler.__class__.__name__].next())
        handler_manager.add_handler(name, handler)

    logger.info("Starting heartbeat")

    heartbeats = []
    start_daemon_thread(functools.partial(heartbeat_thread, heartbeats))

    logger.info("Creating feeds")

    feeds = get_feeds(config)

    for handler in handlers:
        if IFeedsAware.providedBy(handler):
            handler.set_feeds(feeds)

    logger.info("Creating analytics")

    analytics = get_analytics(config)

    logger.info("Setting up web server")

    web_server = setup_web_server(config["web_server"], handler_manager, heartbeats, feeds, analytics)

    logger.info("Creating scheduler")

    celery = Celery()
    celery.config_from_object(config["celery"])
    web_server.celery = celery

    logger.info("Setting up cleanups")

    cleanups = get_cleanups(config)
    setup_cleanup(celery, cleanups, handlers)

    logger.info("Setting up collectors")

    collectors = get_collectors(config)
    setup_collectors(celery, collectors)

    logger.info("Setting up disorders")

    disorder_manager, script_disorder_seekers = get_disorders(config, handlers)
    setup_collector_disorder_seekers(disorder_manager, collectors)
    setup_internal_disorder_seekers(disorder_manager, handler_manager)
    setup_script_disorder_seekers(disorder_manager, celery, script_disorder_seekers)

    handler_manager.add_handler("disorder-manager", disorder_manager)

    disorder_manager.add_observer(web_server)

    logger.info("Setting up processors")

    processors = get_processors(config)

    for processor in processors:
        handler_manager.add_handler("processor-%s" % processor.name, ProcessorRunner(processor, record_fanout))

    logger.info("Starting scheduler")

    celery_beat = celery.Beat(loglevel=args.level)
    celery_beat.set_process_title = lambda: None
    start_daemon_thread(celery_beat.run)
    start_daemon_thread(celery.WorkController(pool_cls="solo").start)

    logger.info("Running")

    while True:
        time.sleep(1)

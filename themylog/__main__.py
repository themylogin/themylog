from __future__ import absolute_import

from celery import Celery
import logging
from Queue import Queue
from threading import Thread

from themylog.cleanup import setup_cleanup
from themylog.collector import setup_collectors
from themylog.config import find_config, read_config
from themylog.config.cleanup import get_cleanups
from themylog.config.collectors import get_collectors
from themylog.config.disorders import get_disorders
from themylog.config.feeds import get_feeds
from themylog.config.handlers import create_handlers
from themylog.config.receivers import create_receivers
from themylog.feed import IFeedsAware
from themylog.web_server import setup_web_server

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    config = read_config(find_config())

    record_queue = Queue()

    # Create and start receivers

    receivers = create_receivers(config)

    def receiver_thread_factory(receiver):
        def receiver_thread():
            for record in receiver.receive():
                record_queue.put(record)

        return receiver_thread

    for receiver in receivers:
        receiver_thread = Thread(target=receiver_thread_factory(receiver))
        receiver_thread.daemon = True
        receiver_thread.start()

    # Create handlers

    handlers = create_handlers(config)

    # Create feeds

    feeds = get_feeds(config)

    for handler in handlers:
        if IFeedsAware.providedBy(handler):
            handler.set_feeds(feeds)

    # Create scheduler

    celery = Celery()
    celery.config_from_object(config["celery"])

    # Set up cleanups

    cleanups = get_cleanups(config)
    setup_cleanup(celery, cleanups, handlers)

    # Set up collectors

    collectors = get_collectors(config)
    setup_collectors(celery, collectors)

    # Start scheduler

    celery_beat = celery.Beat()
    celery_beat.set_process_title = lambda: None
    celery_beat_thread = Thread(target=celery_beat.run)
    celery_beat_thread.daemon = True
    celery_beat_thread.start()

    celery_worker_thread = Thread(target=celery.WorkController(pool_cls="solo").start)
    celery_worker_thread.daemon = True
    celery_worker_thread.start()

    # Web server

    if "web_server" in config:
        setup_web_server(config["web_server"], handlers, feeds)

    # Main loop

    while True:
        record = record_queue.get()
        for handler in handlers:
            handler.handle(record)

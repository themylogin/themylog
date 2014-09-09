from __future__ import absolute_import

from celery import Celery
from celery.app.defaults import DEFAULT_PROCESS_LOG_FMT
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
from themylog.config.processors import get_processors
from themylog.config.receivers import create_receivers
from themylog.disorder.collector import setup_collector_disorder_seekers
from themylog.disorder.script import setup_script_disorder_seekers
from themylog.feed import IFeedsAware
from themylog.processor import run_processor
from themylog.web_server import setup_web_server

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format=DEFAULT_PROCESS_LOG_FMT)
    logger = logging.getLogger(__name__)

    config = read_config(find_config())

    record_queue = Queue()

    logging.info("Creating receivers")

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

    logging.info("Creating handlers")

    handlers = create_handlers(config)

    logging.info("Creating feeds")

    feeds = get_feeds(config)

    for handler in handlers:
        if IFeedsAware.providedBy(handler):
            handler.set_feeds(feeds)

    logging.info("Setting up web server")

    web_server = None
    if "web_server" in config:
        web_server = setup_web_server(config["web_server"], handlers, feeds)

    logging.info("Creating scheduler")

    celery = Celery()
    celery.config_from_object(config["celery"])

    logging.info("Setting up cleanups")

    cleanups = get_cleanups(config)
    setup_cleanup(celery, cleanups, handlers)

    logging.info("Setting up collectors")

    collectors = get_collectors(config)
    setup_collectors(celery, collectors)

    logging.info("Setting up disorders")

    disorder_manager, script_disorder_seekers = get_disorders(config, handlers)
    setup_collector_disorder_seekers(disorder_manager, collectors)
    setup_script_disorder_seekers(disorder_manager, celery, script_disorder_seekers)

    if web_server:
        disorder_manager.add_observer(web_server)

    logging.info("Setting up processors")

    processors = get_processors(config)

    logging.info("Starting scheduler")

    celery_beat = celery.Beat()
    celery_beat.set_process_title = lambda: None
    celery_beat_thread = Thread(target=celery_beat.run)
    celery_beat_thread.daemon = True
    celery_beat_thread.start()

    celery_worker_thread = Thread(target=celery.WorkController(pool_cls="solo").start)
    celery_worker_thread.daemon = True
    celery_worker_thread.start()

    logging.info("Running")

    while True:
        record = record_queue.get()

        for handler in handlers:
            handler.handle(record)

        for processor in processors:
            for result in run_processor(processor, record):
                record_queue.put(result)

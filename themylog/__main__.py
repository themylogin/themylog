import logging
from Queue import Queue
from threading import Thread

from themylog.config import find_config, read_config
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

    # Init disorders

    disorders = get_disorders(config)

    disorders_states = [(None, None) for i, disorder in enumerate(disorders)]

    # Web server

    if "web_server" in config:
        setup_web_server(config["web_server"], handlers, feeds)

    # Main loop

    while True:
        record = record_queue.get()
        for handler in handlers:
            handler.handle(record)

import logging
from Queue import Queue
from threading import Thread

from themylog.config import find_config, read_config
from themylog.config.receivers import create_receivers
from themylog.config.handlers import create_handlers
from themylog.config.feeds import get_feeds
from themylog.feed import IFeedsAware

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    config = read_config(find_config())

    record_queue = Queue()

    """Create and start receivers"""

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

    """Create handlers"""

    handlers = create_handlers(config)

    """Create feeds"""

    feeds = get_feeds(config)

    for handler in handlers:
        if IFeedsAware.providedBy(handler):
            handler.set_feeds(feeds)

    """Main loop"""

    while True:
        record = record_queue.get()
        for handler in handlers:
            handler.handle(record)

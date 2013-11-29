import logging
from Queue import Queue
from threading import Thread

from themylog.config import find_config, read_config, create_receivers, create_storages, get_feeds
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

    for r in receivers:
        receiver_thread = Thread(target=receiver_thread_factory(r))
        receiver_thread.daemon = True
        receiver_thread.start()

    """Create storages"""

    storages = create_storages(config)

    """Create feeds"""

    feeds = get_feeds(config)

    for storage in storages:
        if IFeedsAware.providedBy(storage):
            storage.set_feeds(feeds)

    """Main loop"""

    while True:
        record = record_queue.get()
        for storage in storages:
            storage.persist(record)

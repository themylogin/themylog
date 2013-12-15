from datetime import datetime
import logging

from themylog.config import find_config, read_config, create_storages, get_cleanups
from themylog.storage.interface import ICleaner

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    config = read_config(find_config())

    """Create storages"""

    storages = create_storages(config)
    storages = filter(lambda storage: ICleaner.providedBy(storage), storages)

    if not storages:
        raise Exception("You don't have any storages that implements ICleaner")

    """Get cleanups"""

    cleanups = get_cleanups(config)

    """Do cleanup"""

    for period, feed in cleanups:
        older_than = datetime.now() - period
        for storage in storages:
            storage.cleanup(feed, older_than)

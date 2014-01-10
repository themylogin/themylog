from datetime import datetime
import logging

from themylog.config import find_config, read_config
from themylog.config.handlers import create_handlers
from themylog.config.cleanup import get_cleanups
from themylog.handler.interface import ICleanupCapable

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    config = read_config(find_config())

    """Create handlers"""

    handlers = create_handlers(config)
    handlers = filter(lambda handler: ICleanupCapable.providedBy(handler), handlers)

    if not handlers:
        raise Exception("You don't have any handlers that are ICleanupCapable")

    """Get cleanups"""

    cleanups = get_cleanups(config)

    """Do cleanup"""

    for period, feed in cleanups:
        older_than = datetime.now() - period
        for handler in handlers:
            handler.cleanup(feed, older_than)

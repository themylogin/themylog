from datetime import datetime
import logging
import re
import socket

from themylog.config import find_config, read_config, get_receivers
from themylog.level import levels
from themylog.record import Record
from themylog.record.serializer import serialize_json


class MisconfigurationError(Exception):
    pass


class Client(object):
    def __init__(self, config=None):
        config = read_config(config or find_config())

        for receiver in get_receivers(config):
            if receiver.class_ == "UnixServer":
                self.unix_socket = receiver.args["path"]
                break
        else:
            raise MisconfigurationError("No UnixServer receiver found in %s" % config)

    def log(self, record):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(self.unix_socket)
        s.send(serialize_json(record))
        s.close()


class LoggingHandler(logging.Handler):
    def __init__(self, source, exception_level="debug", loggers_levels={}, config=None):
        super(LoggingHandler, self).__init__()

        self.source = source
        self.exception_level = exception_level
        self.loggers_levels = dict(loggers_levels)

        self.client = Client(config)

    def emit(self, record):
        try:
            rec = Record(datetime=datetime.fromtimestamp(record.created),
                         source=self.source,
                         level=levels[self._get_level(record)],
                         msg="%s.%s" % (record.name, self._underscore_message(str(record.msg))),
                         args=record.__dict__,
                         explanation=self.format(record))
            self.client.log(rec)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def _get_level(self, record):
        if record.exc_info:
            level = self.exception_level
        else:
            level = {
                logging.NOTSET: "unknown",
                logging.DEBUG: "debug",
                logging.INFO: "info",
                logging.WARNING: "warning",
                logging.ERROR: "error",
                logging.CRITICAL: "error",
            }[record.levelno]

        if record.name in self.loggers_levels:
            level = self.loggers_levels[record.name]

        return level

    def _underscore_message(self, msg):
        msg = msg.lower()
        msg = re.sub(r"[^a-z0-9]", "_", msg)
        msg = re.sub(r"_+", "_", msg)
        msg = msg.strip("_")
        return msg


def setup_logging_handler(*args, **kwargs):
    logging.basicConfig(level=logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(LoggingHandler(*args, **kwargs))

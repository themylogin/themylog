from __future__ import absolute_import

from datetime import datetime
import dateutil.parser
import logging
import re

import themyutils.json

from themylog.level import levels, parse_level, repr_level
from themylog.record import Record

logger = logging.getLogger(__name__)


def parse_json(text):
    return Record(**themyutils.json.loads(text))


def parse_plaintext(text, default_datetime=None, default_application=None, default_logger=None,
                    default_level=levels["warning"]):
    datetime_ = default_datetime or datetime.now()
    application = default_application
    logger_ = default_logger
    level = default_level
    msg = ""
    args = {}
    explanation = []

    headers_read = False
    for line in text.split("\n"):
        if headers_read:
            explanation.append(line)
        else:
            if line.strip() == "":
                headers_read = True
            else:
                if "=" in line:
                    key, value = line.split("=", 1)

                    if key == "datetime":
                        try:
                            datetime_ = dateutil.parser.parse(value, dayfirst=True)
                        except ValueError:
                            logger.info("Unable to parse datetime '%s', defaulting to '%s'", value, datetime_)

                    elif key == "application":
                        application = value

                    elif key == "logger":
                        logger_ = value

                    elif key == "level":
                        try:
                            level = parse_level(value)
                        except ValueError:
                            logger.info("Unable to parse level '%s', defaulting to %s", value, repr_level(level))

                    elif key == "msg":
                        msg = value

                    elif key == "args":
                        try:
                            args.update(themyutils.json.loads(value))
                        except ValueError:
                            logger.info("Unable to parse args '%s', defaulting to %s", value, args)

                    else:
                        for cast in (int, float):
                            try:
                                value = cast(value)
                                break
                            except ValueError:
                                pass

                        list_match = re.match("(?P<key>.+)\[(?P<index>0|[1-9][0-9]*)\]$", key)
                        if list_match:
                            key = list_match.group("key")
                            index = int(list_match.group("index"))

                            if key not in args:
                                args[key] = []

                            if index >= len(args[key]):
                                args[key] += [None] * (index - len(args[key]) + 1)

                            args[key][index] = value
                        else:
                            args[key] = value

                else:
                    explanation.append(line)
                    headers_read = True

    return Record(datetime=datetime_, application=application, logger=logger_, level=level, msg=msg, args=args,
                  explanation="\n".join(explanation))

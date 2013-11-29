from __future__ import absolute_import

from datetime import datetime
import dateutil.parser
import json
import logging

from themylog.level import levels, parse_level, repr_level
from themylog.record import Record

logger = logging.getLogger(__name__)


def parse_json(text):
    d = json.loads(text)
    d["datetime"] = dateutil.parser.parse(d["datetime"])
    return Record(**d)


def parse_plaintext(text, default_datetime=None, default_source=None, default_level=levels["warning"]):
    datetime_ = default_datetime or datetime.now()
    source = default_source
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
                    key, value = line.split("=")

                    if key == "datetime":
                        try:
                            datetime_ = dateutil.parser.parse(value, dayfirst=True)
                        except ValueError:
                            logger.info("Unable to parse datetime '%s', defaulting to '%s'", value, datetime_)

                    elif key == "source":
                        source = value

                    elif key == "level":
                        try:
                            level = parse_level(value)
                        except ValueError:
                            logger.info("Unable to parse level '%s', defaulting to %s", value, repr_level(level))

                    elif key == "msg":
                        msg = value

                    elif key == "args":
                        try:
                            args.update(json.loads(value))
                        except ValueError:
                            logger.info("Unable to parse args '%s', defaulting to %s", value, args)

                    else:
                        for cast in (int, float):
                            try:
                                args[key] = cast(value)
                                break
                            except ValueError:
                                pass
                        else:
                            args[key] = value

                else:
                    explanation.append(line)
                    headers_read = True

    return Record(datetime=datetime_, source=source, level=level, msg=msg, args=args,
                  explanation="\n".join(explanation))

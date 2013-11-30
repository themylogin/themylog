import datetime
import json


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()

        try:
            return super(Encoder, self).default(obj)
        except TypeError:
            return repr(obj)


def serialize_json(record):
    return Encoder().encode(record._asdict())

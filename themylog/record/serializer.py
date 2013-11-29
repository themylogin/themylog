import json


class Encoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super(Encoder, self).default(obj)
        except TypeError:
            return repr(obj)


def serialize_json(record):
    d = record._asdict()
    d["datetime"] = d["datetime"].isoformat()
    return Encoder().encode(d)

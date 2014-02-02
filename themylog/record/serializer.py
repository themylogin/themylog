import themylog.json


def serialize_json(record):
    return themylog.json.dumps(record._asdict())

from collections import namedtuple

Record = namedtuple("Record", ["datetime", "source", "level", "msg", "args", "explanation"])

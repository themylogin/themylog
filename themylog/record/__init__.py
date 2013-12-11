from collections import namedtuple

Record = namedtuple("Record", ["datetime", "application", "logger", "level", "msg", "args", "explanation"])

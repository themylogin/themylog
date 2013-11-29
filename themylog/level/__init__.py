from collections import OrderedDict

levels = OrderedDict([
    ("unknown", 0),
    ("debug", 10),
    ("info", 20),
    ("report", 30),
    ("warning", 40),
    ("error", 50),
])

def parse_level(s):
    try:
        return levels[s.strip().lower()]
    except KeyError:
        raise ValueError("Incorrect logging level: '%s'", s)

def repr_level(l):
    for k, v in levels.iteritems():
        if v == l:
            return k
    else:
        return "unknown"

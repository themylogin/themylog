# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

__all__ = [b"get_function"]


def get_function(args, text):
    text_with_header = ("def function(%s):\n    %s" % (args, text.replace("\n", "\n    "))).rstrip()
    try:
        code = compile(text_with_header, "<config>", "single")
    except SyntaxError:
        print text_with_header.encode("utf-8")
        raise
    globals_ = {}
    locals_ = {}
    eval(code, globals_, locals_)
    return locals_["function"]

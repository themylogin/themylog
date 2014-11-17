# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import namedtuple
import zope.interface

__all__ = [b"Disorder", b"MaybeDisorder", b"maybe_with_title", b"IDisorderObserver"]

Disorder = namedtuple("Disorder", ["datetime", "reason", "data"])

MaybeDisorder = namedtuple("MaybeDisorder", ["is_disorder", "disorder"])


def maybe_with_title(maybe, title):
    return dict(maybe._asdict(), title=title)


class IDisorderObserver(zope.interface.Interface):
    def there_is_disorder(self, key, disorder):
        pass

    def there_is_no_disorder(self, key, disorder):
        pass

    def seeker_is_not_functional(self, key):
        pass

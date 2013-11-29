import zope.interface


class Feed(object):
    def __init__(self, tree):
        self.tree = tree

    def contains(self, record):
        return self.make_expr(lambda key: getattr(record, key))

    def make_expr(self, get_record_key, operator_map={}):
        return self.eval(self.tree, get_record_key, operator_map)

    def eval(self, tree, get_record_key, operator_map={}):
        operator = tree[0]
        if operator in operator_map:
            operator = operator_map[operator]

        return operator(*[self._arg(arg, get_record_key, operator_map) for arg in tree[1:]])

    def _arg(self, arg, get_record_key, operator_map={}):
        if isinstance(arg, tuple):
            return self.eval(arg, get_record_key, operator_map=operator_map)

        if callable(arg):
            return arg(get_record_key)

        return arg


class IFeedsAware(zope.interface.Interface):
    def set_feeds(self, feeds):
        pass

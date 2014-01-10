class Evaluator(object):
    def __init__(self, get_record_key, constant_map={}, operator_map={}):
        self.get_record_key = get_record_key
        self.constant_map = constant_map
        self.operator_map = operator_map

    def eval(self, tree):
        operator = tree[0]
        if operator in self.operator_map:
            operator = self.operator_map[operator]

        return operator(*[self._arg(arg) for arg in tree[1:]])

    def _arg(self, arg):
        if arg in self.constant_map:
            return self.constant_map[arg]

        if isinstance(arg, tuple):
            return self.eval(arg)

        if callable(arg):
            return arg(self.get_record_key)

        return arg

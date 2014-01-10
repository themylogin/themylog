import operator
import yaml

from themylog.level import levels


def get_rules_tree(rules, accept_by_default=False):
    if len(rules) == 0:
        return accept_by_default
    else:
        conditions, action = parse_rule(rules[0])

        conditions_tree = get_conditions_tree(conditions.items())
        tail = get_rules_tree(rules[1:])

        if action == "accept":
            return (operator.or_, conditions_tree, tail)
        if action == "reject":
            return (operator.and_, (operator.not_, conditions_tree), tail)
        raise NotImplementedError


def parse_rule(rule):
    if "action" in rule:
        action = rule["action"].lower()
        if action in ["accept", "reject"]:
            conditions = dict(rule)
            del conditions["action"]
            return conditions, action
        else:
            raise Exception("Action should be either 'accept' or 'reject' not '%s'" % action)
    else:
        raise Exception("The following rule must contain action:\n%s" % yaml.dump(rule, default_flow_style=False))


def get_conditions_tree(conditions):
    if len(conditions) == 0:
        return True
    elif len(conditions) == 1:
        return get_condition_tree(*conditions[0])
    else:
        return (operator.and_, get_condition_tree(*conditions[0]), get_conditions_tree(conditions[1:]))


def get_condition_tree(key, value):
    field = lambda get_record_key: get_record_key(key)

    if isinstance(value, list):
        return condition_value_in(field, process_condition_value(key, value))
    else:
        op = operator.eq
        value = value.strip()
        for sym, sym_op in (("!=", operator.ne),
                            ("<=", operator.le),
                            (">=", operator.ge),
                            ("<", operator.lt),
                            (">", operator.gt)):
            if value.startswith(sym):
                op = sym_op
                value = yaml.load(value[len(sym):].strip())
                break

        if isinstance(value, list):
            if op == operator.ne:
                return (operator.not_, condition_value_in(field, process_condition_value(key, value)))
            else:
                raise ValueError("Lists do not support operator %s" % op.__name__)
        else:
            return (op, field, process_condition_value(key, value))


def process_condition_value(key, value):
    if isinstance(value, list):
        return [process_condition_value(key, v) for v in value]

    if key == "level":
        return levels[value]
    else:
        return value


def condition_value_in(field, value):
    if len(value) == 0:
        return False
    elif len(value) == 1:
        return (operator.eq, field, value[0])
    else:
        return (operator.or_, condition_value_in(field, [value[0]]), condition_value_in(field, value[1:]))

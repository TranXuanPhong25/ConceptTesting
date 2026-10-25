"""Literal value graphs; preserves mutable aliasing without pickle or eval."""
import collections
import math


def encode(value, max_nodes=10000, observation=False):
    """observation=True also tags defaultdict/opaque objects; such graphs are compared, never decoded."""
    nodes = []
    seen = {}

    def visit(v, depth=0):
        if depth > 40 or len(nodes) >= max_nodes:
            raise ValueError('value_graph_limit')
        if v is None or type(v) in (bool, int, str):
            if isinstance(v, str) and len(v) > 16000:
                raise ValueError('string_size')
            return {'type': type(v).__name__, 'value': v}
        if type(v) is float:
            if math.isnan(v):
                raise ValueError('nan_value')
            return {'type': 'float', 'value': repr(v)}
        if type(v) is range:
            return {'type': 'range', 'value': [v.start, v.stop, v.step]}
        if observation and type(v) in (collections.Counter, collections.OrderedDict, collections.deque):
            if id(v) in seen:
                return {'ref': seen[id(v)]}
            index = len(nodes); seen[id(v)] = index
            row = {'type': type(v).__name__}
            nodes.append(row)
            row['items'] = ([[visit(k, depth+1), visit(x, depth+1)] for k, x in v.items()] if isinstance(v, dict)
                            else [visit(x, depth+1) for x in v])
            return {'ref': index}
        if observation and isinstance(v, tuple) and hasattr(type(v), '_fields'):
            return {'type': 'namedtuple:' + type(v).__qualname__, 'items': [visit(x, depth+1) for x in v]}
        if observation and type(v) is collections.defaultdict:
            if id(v) in seen:
                return {'ref': seen[id(v)]}
            index = len(nodes); seen[id(v)] = index
            row = {'type': 'defaultdict', 'factory': getattr(v.default_factory, '__name__', repr(v.default_factory))}
            nodes.append(row)
            row['items'] = [[visit(k, depth+1), visit(x, depth+1)] for k, x in v.items()]
            return {'ref': index}
        if observation and type(v) not in (list, tuple, dict, set, frozenset):
            return {'type': 'opaque', 'value': type(v).__qualname__}
        if type(v) not in (list, tuple, dict, set, frozenset):
            raise ValueError('unsupported_value_type:' + type(v).__name__)
        if id(v) in seen:
            return {'ref': seen[id(v)]}
        index = len(nodes)
        seen[id(v)] = index
        row = {'type': type(v).__name__}
        nodes.append(row)
        if isinstance(v, dict):
            row['items'] = [[visit(k, depth+1), visit(x, depth+1)] for k, x in v.items()]
        else:
            values = sorted(v, key=repr) if type(v) in (set, frozenset) else v
            row['items'] = [visit(x, depth+1) for x in values]
        return {'ref': index}

    root = visit(value)
    return {'root': root, 'nodes': nodes}


def decode(graph):
    built = {}
    active_immutable = set()

    def visit(row):
        if 'ref' not in row:
            kind, value = row['type'], row['value']
            if kind == 'float':
                return float(value)
            if kind == 'range':
                return range(*value)
            if kind not in ('NoneType', 'bool', 'int', 'str'):
                raise ValueError('value_graph_scalar')
            return value
        idx = row['ref']
        if idx in built:
            return built[idx]
        if idx in active_immutable:
            raise ValueError('immutable_cycle_unsupported')
        node = graph['nodes'][idx]
        kind = node['type']
        if kind in ('list', 'dict', 'set'):
            value = {'list': list, 'dict': dict, 'set': set}[kind]()
            built[idx] = value
            if kind == 'dict':
                value.update((visit(k), visit(v)) for k, v in node['items'])
            elif kind == 'set':
                value.update(visit(v) for v in node['items'])
            else:
                value.extend(visit(v) for v in node['items'])
        elif kind in ('tuple', 'frozenset'):
            active_immutable.add(idx)
            value = (tuple if kind == 'tuple' else frozenset)(visit(v) for v in node['items'])
            active_immutable.remove(idx)
            built[idx] = value
        else:
            raise ValueError('value_graph_container')
        return value

    return visit(graph['root'])

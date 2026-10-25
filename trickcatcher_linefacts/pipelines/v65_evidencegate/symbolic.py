"""Bounded AST-to-Z3 path evaluation. Unsupported Python is explicit, never UNSAT.

This is a construction instrument, not a normative oracle. No source eval/exec here.
"""
import ast
import copy
from dataclasses import dataclass, field
import itertools
import time
import z3


class Unsupported(Exception):
    pass


@dataclass(frozen=True)
class Seq:
    items: tuple
    kind: str = 'list'


@dataclass(frozen=True)
class Distinct:
    items: tuple


@dataclass(frozen=True)
class Range:
    start: object
    stop: object
    step: int


@dataclass
class State:
    env: dict
    guards: list = field(default_factory=list)
    branches: list = field(default_factory=list)
    events: list = field(default_factory=list)
    status: str = 'normal'
    value: object = None
    event_base: int = 0

    def fork(self):
        return State(dict(self.env), list(self.guards), list(self.branches), list(self.events), self.status, self.value, len(self.events))


def scalar(x):
    if type(x) is bool: return z3.BoolVal(x)
    if type(x) is int: return z3.IntVal(x)
    if type(x) is str: return z3.StringVal(x)
    if isinstance(x, z3.ExprRef): return x
    raise Unsupported('scalar_type:' + type(x).__name__)


def truth(x):
    if x is None: return z3.BoolVal(False)
    if isinstance(x, Seq): return z3.BoolVal(bool(x.items))
    x = scalar(x)
    if z3.is_bool(x): return x
    if z3.is_int(x): return x != 0
    if z3.is_string(x): return z3.Length(x) != 0
    raise Unsupported('truth_type')


def numeric(x):
    x = scalar(x)
    if z3.is_bool(x): return z3.If(x, 1, 0)
    if not z3.is_int(x): raise Unsupported('non_integer_arithmetic')
    return x


def equal(a, b, typed=False):
    if isinstance(a, Range) and isinstance(b, Range):
        # Local range infection means different iteration sequences in this fixed-step catalogue.
        return z3.And(equal(a.start, b.start), equal(a.stop, b.stop), a.step == b.step)
    if isinstance(a, Seq) or isinstance(b, Seq):
        if not isinstance(a, Seq) or not isinstance(b, Seq) or a.kind != b.kind or len(a.items) != len(b.items): return z3.BoolVal(False)
        return z3.And(*[equal(x, y, typed) for x, y in zip(a.items, b.items)])
    if a is None or b is None: return z3.BoolVal(a is None and b is None)
    a, b = scalar(a), scalar(b)
    if a.sort() != b.sort():
        if not typed and (z3.is_bool(a) or z3.is_int(a)) and (z3.is_bool(b) or z3.is_int(b)):
            return numeric(a) == numeric(b)
        return z3.BoolVal(False)
    return a == b


def concrete_int(value):
    value = z3.simplify(numeric(value))
    if not z3.is_int_value(value): raise Unsupported('symbolic_shape_or_step')
    return value.as_long()


def ite(c, a, b):
    if isinstance(a, Seq) and isinstance(b, Seq) and a.kind == b.kind and len(a.items) == len(b.items):
        return Seq(tuple(ite(c, x, y) for x, y in zip(a.items, b.items)), a.kind)
    if a is None and b is None: return None
    a, b = scalar(a), scalar(b)
    if a.sort() != b.sort(): raise Unsupported('conditional_mixed_types')
    return z3.If(c, a, b)


class Evaluator:
    def __init__(self, source, entry, hypothesis, variant=False, max_steps=6, max_paths=128, deadline=None):
        self.tree = ast.parse(source)
        from .bindings import resolve
        self.fn, self.method_wrapper = resolve(self.tree, entry)
        self.hypothesis, self.variant = hypothesis, variant
        self.max_steps, self.max_paths = max_steps, max_paths
        self.deadline = deadline
        self.issues = set()
        self.node_count = 0
        self.global_bindings = set()
        for n in self.tree.body:
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                self.global_bindings.add(n.name)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                self.global_bindings.update(a.asname or a.name.split('.')[0] for a in n.names)
            elif isinstance(n, (ast.Assign, ast.AnnAssign)):
                self.global_bindings.update(x.id for x in ast.walk(n) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store))
        from .hypotheses import replacement
        self.alt = replacement(hypothesis)
        if self.fn.args.vararg or self.fn.args.kwarg or self.fn.args.kwonlyargs or self.fn.args.defaults:
            raise Unsupported('variable_keyword_or_default_arguments')
        # Aliases are allowed only as immutable values. No element writes/mutating calls are supported.
        for n in ast.walk(self.fn):
            if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n is not self.fn:
                raise Unsupported('nested_function')

    def target(self, node):
        from .hypotheses import span
        return hasattr(node, 'end_lineno') and span(node) == self.hypothesis['span'] and type(node).__name__ == self.hypothesis['node_kind']

    def expr(self, node, s, bypass=False):
        self.node_count += 1
        if self.deadline is not None and time.monotonic() >= self.deadline: raise Unsupported('symbolic_deadline')
        if self.node_count > 100000: raise Unsupported('expression_budget')
        if not bypass and self.target(node):
            if self.variant: return self.expr(self.alt, s, True)
            value = self.expr(node, s, True)
            other = s.fork()
            alt = self.expr(self.alt, other, True)
            obligation = z3.Not(equal(value, alt, typed=True))
            if 'ORDER_TIE' in self.hypothesis['facets'] and isinstance(node, ast.Compare):
                obligation = z3.And(obligation, equal(self.expr(node.left, other), self.expr(node.comparators[0], other)))
            if self.hypothesis['family'] == 'MULTIPLICITY' and isinstance(node, ast.Call):
                seq = self.expr(node.args[0], other)
                if isinstance(seq, Distinct): seq = Seq(seq.items)
                if not isinstance(seq, Seq): raise Unsupported('multiplicity_requires_sequence')
                pairs = [equal(x, y) for i, x in enumerate(seq.items) for y in seq.items[i + 1:]]
                obligation = z3.And(obligation, z3.Or(*pairs))
            s.events.append(dict(reach=z3.And(*s.guards), condition=z3.And(*other.guards, obligation), before=value, after=alt))
            return value
        if isinstance(node, ast.Constant):
            if node.value is None or type(node.value) in (int, bool, str): return node.value
            raise Unsupported('constant_type')
        if isinstance(node, ast.Name):
            if node.id not in s.env: raise Unsupported('unknown_name:' + node.id)
            return s.env[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            return Seq(tuple(self.expr(x, s) for x in node.elts), 'list' if isinstance(node, ast.List) else 'tuple')
        if isinstance(node, ast.UnaryOp):
            v = self.expr(node.operand, s)
            if isinstance(node.op, ast.Not): return z3.Not(truth(v))
            if isinstance(node.op, ast.USub): return -numeric(v)
            if isinstance(node.op, ast.UAdd): return numeric(v)
            raise Unsupported('unary_operator')
        if isinstance(node, ast.BinOp):
            return self.binary(node.op, self.expr(node.left, s), self.expr(node.right, s), s)
        if isinstance(node, ast.Compare):
            left = self.expr(node.left, s); result = z3.BoolVal(True)
            for op, rightnode in zip(node.ops, node.comparators):
                right_state = s.fork()
                right_state.guards.append(result)
                right = self.expr(rightnode, right_state)
                # Later comparison operands are evaluated only if previous comparisons hold.
                self.merge_conditional(s, right_state, result)
                if isinstance(op, ast.Eq): term = equal(left, right)
                elif isinstance(op, ast.NotEq): term = z3.Not(equal(left, right))
                elif isinstance(op, (ast.In, ast.NotIn)):
                    if isinstance(right, Seq): term = z3.Or(*[equal(left, x) for x in right.items])
                    elif z3.is_string(scalar(right)): term = z3.Contains(scalar(right), scalar(left))
                    else: raise Unsupported('membership_type')
                    if isinstance(op, ast.NotIn): term = z3.Not(term)
                else:
                    a, b = numeric(left), numeric(right)
                    term = {ast.Lt: lambda: a < b, ast.LtE: lambda: a <= b, ast.Gt: lambda: a > b, ast.GtE: lambda: a >= b}.get(type(op))
                    if term is None: raise Unsupported('comparison_operator')
                    term = term()
                result = z3.And(result, term); left = right
            return result
        if isinstance(node, ast.BoolOp):
            value = self.expr(node.values[0], s)
            for nextnode in node.values[1:]:
                condition = truth(value) if isinstance(node.op, ast.And) else z3.Not(truth(value))
                branch = s.fork(); branch.guards.append(condition)
                other = self.expr(nextnode, branch)
                self.merge_conditional(s, branch, condition)
                value = ite(condition, other, value)
            return value
        if isinstance(node, ast.IfExp):
            c = truth(self.expr(node.test, s)); a = s.fork(); b = s.fork()
            a.guards.append(c); b.guards.append(z3.Not(c))
            va, vb = self.expr(node.body, a), self.expr(node.orelse, b)
            self.merge_conditional(s, a, c); self.merge_conditional(s, b, z3.Not(c))
            return ite(c, va, vb)
        if isinstance(node, ast.Subscript):
            seq = self.expr(node.value, s)
            if isinstance(node.slice, ast.Slice):
                if not isinstance(seq, Seq): raise Unsupported('string_slice')
                fields = [None if v is None else concrete_int(self.expr(v, s)) for v in (node.slice.lower, node.slice.upper, node.slice.step)]
                return Seq(seq.items[slice(*fields)], seq.kind)
            idx = numeric(self.expr(node.slice, s))
            length = len(seq.items) if isinstance(seq, Seq) else z3.Length(scalar(seq))
            normalized = z3.If(idx < 0, idx + length, idx)
            s.guards.append(z3.And(normalized >= 0, normalized < length))
            if isinstance(seq, Seq):
                if not seq.items: return 0  # impossible under the bounds above
                value = seq.items[-1]
                for i in reversed(range(len(seq.items) - 1)): value = ite(normalized == i, seq.items[i], value)
                return value
            if z3.is_string(scalar(seq)): return z3.SubString(scalar(seq), normalized, 1)
            raise Unsupported('subscript_type')
        if isinstance(node, ast.Call): return self.call(node, s)
        raise Unsupported('expression:' + type(node).__name__)

    @staticmethod
    def merge_conditional(s, branch, condition):
        s.guards.append(z3.Implies(condition, z3.And(*branch.guards)))
        for event in branch.events[branch.event_base:]:
            s.events.append(dict(event, reach=z3.And(condition, event['reach']), condition=z3.And(condition, event['condition'])))

    def binary(self, op, a, b, s):
        if isinstance(op, ast.Add) and isinstance(a, Seq) and isinstance(b, Seq):
            if a.kind != b.kind: raise Unsupported('mixed_sequence_concat')
            if len(a.items) + len(b.items) > 64: raise Unsupported('symbolic_sequence_size')
            return Seq(a.items + b.items, a.kind)
        if isinstance(op, ast.Add) and not isinstance(a, Seq) and not isinstance(b, Seq) and z3.is_string(scalar(a)) and z3.is_string(scalar(b)):
            return z3.Concat(scalar(a), scalar(b))
        a, b = numeric(a), numeric(b)
        if isinstance(op, ast.Add): return a + b
        if isinstance(op, ast.Sub): return a - b
        if isinstance(op, ast.Mult): return a * b
        if isinstance(op, (ast.FloorDiv, ast.Mod)):
            s.guards.append(b != 0)
            quotient = z3.ToInt(z3.ToReal(a) / z3.ToReal(b))
            return quotient if isinstance(op, ast.FloorDiv) else a - b * quotient
        raise Unsupported('binary_operator:' + type(op).__name__)

    def call(self, node, s):
        if not isinstance(node.func, ast.Name) or node.keywords: raise Unsupported('method_external_or_keyword_call')
        name = node.func.id
        if name in s.env or name in self.global_bindings:
            raise Unsupported('shadowed_callable:' + name)
        args = [self.expr(x, s) for x in node.args]
        if name == 'len' and len(args) == 1:
            seq = args[0]
            if isinstance(seq, Seq): return len(seq.items)
            if isinstance(seq, Distinct): return z3.Sum(*self.unique_flags(seq.items))
            if z3.is_string(scalar(seq)): return z3.Length(scalar(seq))
        if name == 'set' and len(args) == 1 and isinstance(args[0], Seq): return Distinct(args[0].items)
        if name == 'sum' and 1 <= len(args) <= 2:
            seq = args[0]; start = args[1] if len(args) == 2 else 0
            if isinstance(seq, Seq): return numeric(start) + z3.Sum(*[numeric(x) for x in seq.items])
            if isinstance(seq, Distinct):
                return numeric(start) + z3.Sum(*[z3.If(flag == 1, numeric(x), 0) for flag, x in zip(self.unique_flags(seq.items), seq.items)])
        if name in ('min', 'max'):
            items = args[0].items if len(args) == 1 and isinstance(args[0], Seq) else args
            if not items:
                s.guards.append(z3.BoolVal(False)); return 0
            result = numeric(items[0])
            for item in items[1:]:
                v = numeric(item); result = z3.If(v < result if name == 'min' else v > result, v, result)
            return result
        if name == 'abs' and len(args) == 1:
            v = numeric(args[0]); return z3.If(v < 0, -v, v)
        if name == 'range' and 1 <= len(args) <= 3:
            start, stop = (0, args[0]) if len(args) == 1 else args[:2]
            step = concrete_int(args[2]) if len(args) == 3 else 1
            if step == 0: s.guards.append(z3.BoolVal(False)); step = 1
            return Range(numeric(start), numeric(stop), step)
        if name == 'enumerate' and len(args) == 1 and isinstance(args[0], Seq):
            return Seq(tuple(Seq((i, x), 'tuple') for i, x in enumerate(args[0].items)))
        if name in ('list', 'tuple', 'reversed') and len(args) == 1 and isinstance(args[0], Seq):
            seq = args[0]
            return Seq(tuple(reversed(seq.items)) if name == 'reversed' else seq.items, 'tuple' if name == 'tuple' else 'list')
        if name in ('all', 'any') and len(args) == 1 and isinstance(args[0], Seq):
            return (z3.And if name == 'all' else z3.Or)(*[truth(x) for x in args[0].items])
        raise Unsupported('call:' + name)

    @staticmethod
    def unique_flags(items):
        return [z3.If(z3.And(*[z3.Not(equal(x, y)) for y in items[:i]]), 1, 0) for i, x in enumerate(items)]

    def assign(self, target, value, s):
        if isinstance(target, ast.Name): s.env[target.id] = value; return
        if isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, Seq) and len(target.elts) == len(value.items):
            for t, v in zip(target.elts, value.items): self.assign(t, v, s)
            return
        raise Unsupported('assignment_target_or_unpack')

    def statement(self, node, s):
        if self.target(node) and isinstance(node, ast.AugAssign):
            before_state, after_state = s.fork(), s.fork()
            if isinstance(self.expr(node.target, before_state), Seq):
                raise Unsupported('inplace_sequence_mutation')
            before = self.binary(node.op, self.expr(node.target, before_state), self.expr(node.value, before_state), before_state)
            if isinstance(self.alt, ast.Assign): after = self.expr(self.alt.value, after_state)
            elif isinstance(self.alt, ast.AugAssign): after = self.binary(self.alt.op, self.expr(self.alt.target, after_state), self.expr(self.alt.value, after_state), after_state)
            else: raise Unsupported('augassign_alternative')
            if self.variant:
                s.guards = after_state.guards
                self.assign(self.alt.targets[0] if isinstance(self.alt, ast.Assign) else self.alt.target, after, s)
            else:
                s.guards = before_state.guards
                s.events.append(dict(reach=z3.And(*s.guards), condition=z3.And(*after_state.guards, z3.Not(equal(before, after, typed=True))), before=before, after=after))
                self.assign(node.target, before, s)
            return [s]
        if isinstance(node, ast.Return):
            s.value = self.expr(node.value, s) if node.value else None; s.status = 'return'; return [s]
        if isinstance(node, ast.Assign):
            v = self.expr(node.value, s)
            for t in node.targets: self.assign(t, v, s)
            return [s]
        if isinstance(node, ast.AnnAssign) and node.value:
            self.assign(node.target, self.expr(node.value, s), s); return [s]
        if isinstance(node, ast.AugAssign):
            if isinstance(self.expr(node.target, s), Seq): raise Unsupported('inplace_sequence_mutation')
            self.assign(node.target, self.binary(node.op, self.expr(node.target, s), self.expr(node.value, s), s), s); return [s]
        if isinstance(node, ast.If):
            condition = truth(self.expr(node.test, s)); out = []
            for value, body in ((True, node.body), (False, node.orelse)):
                t = s.fork(); t.guards.append(condition if value else z3.Not(condition))
                t.branches.append(dict(line=node.lineno, value=value, predicate=ast.unparse(node.test)))
                out += self.block(body, [t])
            return out
        if isinstance(node, ast.For):
            seq = self.expr(node.iter, s)
            if isinstance(seq, Range):
                items = [seq.start + i * seq.step for i in range(self.max_steps)]
                conditions = [(v < seq.stop if seq.step > 0 else v > seq.stop) for v in items]
                exhausted = seq.start + self.max_steps * seq.step
                overflow = exhausted < seq.stop if seq.step > 0 else exhausted > seq.stop
            elif isinstance(seq, Seq):
                if len(seq.items) > self.max_steps: raise Unsupported('loop_bound')
                items, conditions, overflow = seq.items, [z3.BoolVal(True)] * len(seq.items), z3.BoolVal(False)
            else: raise Unsupported('for_iterable')
            active, done = [s], []
            for item, condition in zip(items, conditions):
                following = []
                for state in active:
                    leave = state.fork(); leave.guards.append(z3.Not(condition))
                    done += self.block(node.orelse, [leave])
                    go = state.fork(); go.guards.append(condition)
                    self.assign(node.target, item, go)
                    for t in self.block(node.body, [go]):
                        if t.status == 'break': t.status = 'normal'; done.append(t)
                        elif t.status == 'return': done.append(t)
                        else: t.status = 'normal'; following.append(t)
                active = self.limit(following)
            for state in active:
                if isinstance(seq, Range): self.issues.add('range_execution_bounded')
                state.guards.append(z3.Not(overflow))
                done += self.block(node.orelse, [state])
            return self.limit(done)
        if isinstance(node, ast.Break): s.status = 'break'; return [s]
        if isinstance(node, ast.Continue): s.status = 'continue'; return [s]
        if isinstance(node, ast.Pass): return [s]
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant): return [s]
        if isinstance(node, ast.Assert):
            s.guards.append(truth(self.expr(node.test, s))); return [s]
        raise Unsupported('statement:' + type(node).__name__)

    def limit(self, states):
        # Drop syntactically impossible paths before the explicit resource cap.
        states = [s for s in states if not z3.is_false(z3.simplify(z3.And(*s.guards)))]
        if len(states) > self.max_paths:
            self.issues.add('path_cap')
            states = states[:self.max_paths]
        return states

    def block(self, body, states):
        for node in body:
            if self.deadline is not None and time.monotonic() >= self.deadline:
                self.issues.add('symbolic_deadline'); return []
            out = []
            for s in states:
                if s.status != 'normal': out.append(s); continue
                try: out += self.statement(node, s)
                except (Unsupported, z3.Z3Exception, TypeError, ValueError) as exc:
                    self.issues.add(str(exc)[:160])
            states = self.limit(out)
        return states

    def run(self, arguments):
        names = [x.arg for x in self.fn.args.posonlyargs + self.fn.args.args]
        if self.method_wrapper: names = names[1:]
        if len(names) != len(arguments): raise Unsupported('arity')
        states = self.block(self.fn.body, [State(dict(zip(names, arguments)))])
        return [s for s in states if s.status in ('normal', 'return')]


def input_shapes(seeds, max_seq_len=6, max_shapes=32):
    if not seeds: raise Unsupported('public_examples_required_for_type_profile')
    arity = len(seeds[0]); choices = []
    if any(len(seed) != arity for seed in seeds): raise Unsupported('inconsistent_arity')
    for i in range(arity):
        values = [s[i] for s in seeds]
        kinds = {type(v) for v in values}
        if len(kinds) != 1: raise Unsupported('heterogeneous_argument_types')
        kind = type(values[0])
        if kind in (int, bool, str): choices.append([(kind.__name__, None)])
        elif kind in (list, tuple):
            elems = [v for value in values for v in value]
            types = {type(v) for v in elems}
            if len(types) > 1 or (types and next(iter(types)) not in (int, bool, str)):
                raise Unsupported('heterogeneous_or_nested_input_sequence')
            if not types: raise Unsupported('empty_only_sequence_element_type_unknown')
            element = next(iter(types)).__name__
            lengths = list(range(max_seq_len + 1))
            choices.append([(kind.__name__, (element, n)) for n in lengths if n <= max_seq_len])
        else: raise Unsupported('input_type:' + kind.__name__)
    all_shapes = itertools.product(*choices)
    shapes = list(itertools.islice(all_shapes, max_shapes))
    truncated = next(all_shapes, None) is not None
    return shapes, truncated


def symbolic_inputs(shape, int_bound, max_seq_len):
    constraints = []
    def atom(name, kind):
        if kind == 'int':
            v = z3.Int(name); constraints.extend([v >= -int_bound, v <= int_bound]); return v
        if kind == 'bool': return z3.Bool(name)
        if kind == 'str':
            v = z3.String(name)
            constraints.append(z3.Length(v) <= max_seq_len)
            return v
        raise Unsupported('atom_type')
    args = []
    for i, (kind, spec) in enumerate(shape):
        if spec is None: args.append(atom(f'arg{i}', kind))
        else:
            element, n = spec
            args.append(Seq(tuple(atom(f'arg{i}_{j}', element) for j in range(n)), kind))
    return args, constraints


def materialize(value, model):
    if isinstance(value, Range):
        return range(materialize(value.start, model), materialize(value.stop, model), value.step)
    if isinstance(value, Seq):
        xs = [materialize(x, model) for x in value.items]
        return tuple(xs) if value.kind == 'tuple' else xs
    if value is None: return None
    val = model.eval(scalar(value), model_completion=True)
    if z3.is_bool(val): return z3.is_true(val)
    if z3.is_int_value(val): return val.as_long()
    if z3.is_string_value(val): return val.as_string()
    raise Unsupported('model_value')

"""CPU-only, observed def-use / AST guard / lexical docstring relations.

The input is the frozen v7 selection, never a newly ranked list. Trace records
can be supplied by callers; otherwise replay base calls and selected witnesses
with the unchanged tracer. This module's output never contains witness inputs.
Tracing uses global tracer state and signals: call extract sequentially, outside
generation worker threads. Missing evidence yields missing edges, not guesses.
"""
import ast
import collections
import re
from . import tracer

VERSION = 'ast-trace-lexical-v1'
OP_WORDS = {
    ast.Lt: 'less smaller below', ast.LtE: 'less smaller below equal',
    ast.Gt: 'greater larger above', ast.GtE: 'greater larger above equal',
    ast.Eq: 'equal same', ast.NotEq: 'different unequal',
    ast.Add: 'add sum total', ast.Sub: 'subtract difference',
    ast.Mult: 'multiply product', ast.Div: 'divide quotient',
    ast.Mod: 'remainder modulo divisible', ast.In: 'contain member',
    ast.NotIn: 'contain absent', ast.Not: 'not empty',
}
STOP = set('a an the of to in is are if for from with and or this that given return'.split())


def words(text):
    # Identifiers split at underscores; deterministic lowercase plural stripping.
    return {w[:-1] if len(w) > 3 and w.endswith('s') else w
            for w in re.findall(r'[a-z]+', text.lower()) if w not in STOP}


def clauses(fn):
    doc = (ast.get_docstring(fn) or '').split('>>>', 1)[0]
    doc = ' '.join(doc.split())
    return [c.strip() for c in re.split(r'(?<=[.!?])\s+', doc) if c.strip()]


def collect_traces(task):
    """Replay trusted PUTs using the original tracer's time/step limits."""
    code, sites = tracer.instrument(task['put'])
    # Match facts.py: collect base calls on the uninstrumented PUT, then trace.
    original = tracer.load_module(task['put'])
    base_args, base_ok = tracer.run_base(original[task['entry']], task['base'], ns=original)
    ns = tracer.load_module(code, tracer.HOOKS)
    fn = ns[task['entry']]
    base = [tracer.trace(fn, args) for args in base_args]
    witnesses = []
    for fact in task['concept_meta']:
        raw = fact.get('witness_call')
        if raw:
            call = ast.parse(raw, mode='eval').body
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != task['entry']:
                raise ValueError('invalid selected witness call')
            args = ([ast.literal_eval(a) for a in call.args],
                    {k.arg: ast.literal_eval(k.value) for k in call.keywords})
        elif 'witness_args' in fact:
            args = (fact['witness_args'], {})
        else:
            continue
        witnesses.append(tracer.trace(fn, args))
    return sites, base, witnesses, base_ok


def _cells(traces):
    return set().union(*(set(map(tuple, t[0])) for t in traces)) if traces else set()


def extract(task, *, sites=None, base_traces=None, witness_traces=None):
    tree = ast.parse(task['put'])
    fn = next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
              and n.name == task['entry'])
    base_ok = None
    if sites is None or base_traces is None:
        sites, base_traces, witness_traces, base_ok = collect_traces(task)
    base = _cells(base_traces)
    base_statuses = dict(collections.Counter(t[2] for t in base_traces))
    witness_statuses = dict(collections.Counter(t[2] for t in witness_traces or []))
    observed = base | _cells(witness_traces or [])
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    sentences = clauses(fn)
    rows = []
    for index, fact in enumerate(task['concept_meta']):
        # SPEC facts have no executable site: anchor them at the parameter definition.
        line = fact.get('line', fn.lineno)
        candidates = [n for n in ast.walk(fn) if isinstance(n, ast.stmt) and n.lineno == line]
        if not candidates:
            candidates = [n for n in ast.walk(fn) if isinstance(n, ast.expr) and n.lineno == line]
        node = min(candidates, key=lambda n: (getattr(n, 'end_lineno', n.lineno)-n.lineno,
                                             n.col_offset)) if candidates else fn
        site_nodes = [n for n in ast.walk(fn) if getattr(n, 'lineno', None) == line]
        identifiers = {n.id for n in site_nodes if isinstance(n, ast.Name)}
        params = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
        if fact.get('input_class'):
            identifiers = {params[fact['input_class']['param']].arg}
        elif line == fn.lineno:
            identifiers = {a.arg for a in params}
            cell = fact.get('cell', [None, ''])[1]
            if cell.startswith('P|'):
                identifiers = {params[int(cell.split('|')[1])].arg}
        data = []
        for sid, label in sorted(observed):
            if sid != -2 or not label.startswith('du|'):
                continue
            _, scope, name, definition, use, kind = label.split('|')
            # Tracer scope identifies the enclosing function; don't mix same-line helpers.
            owner = node
            while owner not in (fn, tree) and not isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                owner = parents[owner]
            if int(use) == line and int(scope) == owner.lineno:
                data.append(dict(name=name, definition=int(definition), use=line, kind=kind,
                                 evidence='observed def-use'))
        controls = []
        child = node
        while child in parents:
            parent = parents[child]
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                break
            if isinstance(parent, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                if child in parent.body or child in parent.orelse:
                    # Loop else requires exhaustion without break, not simply
                    # a False/zero-iteration outcome. No such probe exists.
                    if not isinstance(parent, ast.If) and child in parent.orelse:
                        child = parent
                        continue
                    required = 'T' if child in parent.body else 'F'
                    is_for = isinstance(parent, (ast.For, ast.AsyncFor))
                    expression = ('for ' + ast.unparse(parent.target) + ' in ' + ast.unparse(parent.iter)
                                  if is_for else ast.unparse(parent.test))
                    condition_line = parent.lineno if is_for else parent.test.lineno
                    ids = [i for i, s in enumerate(sites) if s['line'] == condition_line
                           and s['kind'] == ('loop' if is_for else 'cond') and s['src'] == expression]
                    seen = set()
                    for s, value in base:
                        if s not in ids: continue
                        if value in ('T', 'F'): seen.add(value)
                        if is_for and value.startswith('loop:'):
                            seen.add('T' if int(value[5:]) else 'F')
                    status = ('not evaluated' if not seen else 'never' if required not in seen
                              else 'always' if seen == {required} else 'sometimes')
                    if base_statuses.get('timeout'):
                        status = 'unknown (incomplete base trace)'
                    controls.append(dict(line=condition_line, condition=expression,
                                         outcome=required, base=status,
                                         evidence='AST enclosing guard; base tracer'))
            child = parent
        controls.reverse()
        terms = set().union(*(words(i) for i in identifiers)) if identifiers else set()
        for n in site_nodes:
            terms |= words(OP_WORDS.get(type(n), ''))
        scores = [len(terms & words(s)) for s in sentences]
        best = max(range(len(scores)), key=lambda i: scores[i]) if scores else None
        spec = (dict(clause=best+1, text=sentences[best], overlap=scores[best], evidence='lexical overlap')
                if best is not None and scores[best] > 0 else None)
        row = dict(hint_index=index, line=line, site='parameter definition' if 'line' not in fact else 'line',
                   data=data, control=controls, spec=spec)
        rows.append(row)
    return dict(version=VERSION, base_ok=base_ok, base_trace_statuses=base_statuses,
                witness_trace_statuses=witness_statuses, hints=rows)


def render(row, include_spec=True):
    parts = []
    if include_spec and row['spec']:
        s = row['spec']
        parts.append(f"spec clause R{s['clause']} [spec-link, lexical]: {s['text']}")
    for c in row['control']:
        parts.append(f"condition line {c['line']} [control]: `{c['condition']}`; {c['outcome']} branch {c['base']} taken by base tests (among evaluations)")
    parts.append(f"line {row['line']} ({row['site']})")
    chain = ' -> '.join(parts)
    for d in row['data']:
        chain += f" <- value `{d['name']}` from line {d['definition']} [data, {d['kind']}, observed]"
    return chain

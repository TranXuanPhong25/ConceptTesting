"""Explicit fault-type concepts: (a) site + fault type from mutation operators, ranked by tool evidence;
(b) task-agnostic input templates per fault type applied to the public base inputs.

Pure functions only (no code execution). Fault types follow the simple-bug pattern families of ManySStuBs4J /
PySStuBs (Karampatsis & Allamanis 2020; Kamienski et al. 2021): change of comparison boundary or numeric literal,
change of operator, change of operand/value, wrong call/argument, plus missing case (not expressible as a PUT mutant).
"""
import ast
from itertools import zip_longest

TYPES = ('BOUNDARY', 'OPERATOR', 'VALUE', 'CALL', 'MISSING_CASE')
TYPE_TEXT = {
    'BOUNDARY': 'off-by-one: a comparison boundary, numeric literal, index or range bound is one off',
    'OPERATOR': 'wrong operator: relational, arithmetic, boolean or negation operator, or break/continue',
    'VALUE': 'wrong value: wrong variable, constant or assigned value',
    'CALL': 'wrong call: wrong function, method or argument',
    'MISSING_CASE': 'missing case: an input class (empty, single element, all equal, zero, minimal) is not handled',
}
PRIORITY = {t: i for i, t in enumerate(TYPES)}
MAX_PER_TYPE = 120
MAX_TOTAL = 480
MAX_REPR = 1500


# ---- (a) fault type of a mutant -----------------------------------------------------------------------------------
def _int_text(text):
    try:
        v = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None
    return v if type(v) is int else None


def fault_type(mutant, line_text):
    """mutant: v4_tools.enumerate_mutants row (family, operator, boundary, before, after)."""
    family = mutant['family']
    if family == 'ROR' and mutant['boundary']:
        return 'BOUNDARY'
    if family == 'CRP constant':
        a, b = _int_text(mutant['before']), _int_text(mutant['after'])
        index_like = 'range(' in line_text or '[' in line_text or 'len(' in line_text
        if a is not None and b is not None and abs(a - b) == 1 and (mutant['boundary'] or index_like):
            return 'BOUNDARY'
        return 'VALUE'
    if family in ('ROR', 'AOR', 'COR', 'UOI/negation', 'BCR'):
        return 'OPERATOR'
    if family in ('name replacement', 'assignment replacement', 'dictionary-key replacement'):
        return 'VALUE'
    return 'CALL'  # argument replacement/removal, lambda result, string-method replacement, case deletion


def site_constants(source, line):
    """Integer literals on the site line (path-condition constants), plus 0 and 1."""
    out = {0, 1}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return sorted(out)
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and type(n.value) is int and getattr(n, 'lineno', None) == line and abs(n.value) <= 10 ** 6:
            out.add(n.value)
    return sorted(out)


# ---- (b) templates ------------------------------------------------------------------------------------------------
def positions(args):
    """(path, value) for each argument and each element of a top-level list/tuple argument (depth <= 2)."""
    out = []
    for i, a in enumerate(args):
        out.append(((i,), a))
        if type(a) in (list, tuple):
            for j, x in enumerate(a[:12]):
                out.append(((i, j), x))
    return out


def replace(args, path, value):
    args = list(args)
    if len(path) == 1:
        args[path[0]] = value
    else:
        seq = list(args[path[0]])
        seq[path[1]] = value
        args[path[0]] = type(args[path[0]])(seq)
    return tuple(args)


def _resize(s, n):
    if n <= len(s):
        return s[:n]
    if not s:
        return None
    reps = (n // len(s)) + 1
    return (s * reps)[:n]


def _seq(v):
    return type(v) in (list, tuple, str)


def _num(v):
    return type(v) is int


def ops_boundary(v, consts):
    if _num(v):
        yield 'v-1', v - 1
        yield 'v+1', v + 1
        for c in consts:
            for d in (-1, 0, 1):
                yield f'const {c}{d:+d}', c + d
    elif _seq(v):
        yield 'len-1', v[:-1]
        if v:
            yield 'len+1', v + v[-1:]
        for c in consts:
            if 0 <= c <= 2 * len(v) + 2:
                r = _resize(v, c)
                if r is not None:
                    yield f'len={c}', r


def ops_operator(v, consts):
    if _num(v):
        yield 'zero', 0
        yield 'negate', -v
    elif type(v) is bool:
        yield 'not', not v
    elif _seq(v) and v:
        if len(v) >= 2:
            yield 'tie first two', v[:1] * 2 + v[2:]
        yield 'all equal', v[:1] * len(v)
        if type(v) is not str:
            try:
                yield 'sorted', type(v)(sorted(v))
            except TypeError:
                pass
        yield 'reversed', v[::-1]


def ops_value(v, consts):
    if _num(v):
        yield 'v+2', v + 2
        yield 'v-2', v - 2
    elif type(v) is str and v:
        yield 'swapcase', v.swapcase()
        yield 'reverse', v[::-1]
        if len(v) >= 2:
            yield 'swap ends', v[-1] + v[1:-1] + v[0]
    elif type(v) in (list, tuple) and v:
        if len(v) >= 2:
            yield 'swap ends', type(v)([v[-1]] + list(v[1:-1]) + [v[0]])
        nums = [x for x in v if _num(x)]
        if len(nums) == len(v):
            yield 'append max+1', type(v)(list(v) + [max(nums) + 1])
            yield 'first=min-1', type(v)([min(nums) - 1] + list(v[1:]))


def ops_call(v, consts):
    if type(v) is str:
        yield 'upper', v.upper()
        yield 'lower', v.lower()
        yield 'pad spaces', ' ' + v + ' '
    elif type(v) in (list, tuple) and len(v) >= 2:
        yield 'rotate', type(v)(list(v[1:]) + [v[0]])
        try:
            yield 'sorted desc', type(v)(sorted(v, reverse=True))
        except TypeError:
            pass
        uniq = list(dict.fromkeys(v)) if all(isinstance(x, (int, str, bool)) for x in v) else None
        if uniq is not None and len(uniq) < len(v):
            yield 'dedupe', type(v)(uniq)
        elif uniq is not None:
            yield 'duplicate middle', type(v)(list(v[:len(v) // 2 + 1]) + list(v[len(v) // 2:]))


def ops_missing(v, consts):
    if _num(v):
        for c in (0, 1, -1):
            yield f'={c}', c
    elif _seq(v):
        yield 'empty', v[:0]
        yield 'single', v[:1]
        if len(v) > 2:
            yield 'two', v[:2]
        if len(v) >= 2:
            yield 'all equal', v[:1] * len(v)


OPS = {'BOUNDARY': ops_boundary, 'OPERATOR': ops_operator, 'VALUE': ops_value, 'CALL': ops_call, 'MISSING_CASE': ops_missing}


def ok_literal(args):
    try:
        text = repr(args)
        return len(text) <= MAX_REPR and ast.literal_eval(text) == args
    except (ValueError, SyntaxError, RecursionError, MemoryError):
        return False


def _chars(text):
    return {('lower' if c.islower() else 'upper' if c.isupper() else 'digit' if c.isdigit() else c) for c in text}


def domain_profile(seeds):
    """Public-information domain per argument position (from the public examples only, never the evaluator contract):
    integer lower bound (>=1 / >=0 if every public value is), minimum sequence length, and string character classes."""
    prof = {}
    for seed in seeds:
        for path, v in positions(seed):
            key = path if len(path) == 1 else (path[0], '*')
            q = prof.setdefault(key, dict(ints=[], lens=[], chars=set(), types=set()))
            q['types'].add(type(v).__name__)
            if _num(v):
                q['ints'].append(v)
            if _seq(v):
                q['lens'].append(len(v))
            if type(v) is str:
                q['chars'] |= _chars(v)
            if type(v) in (list, tuple):
                for x in v:
                    if type(x) is str:
                        q['chars'] |= _chars(x)
    return prof


def in_domain(args, prof):
    for path, v in positions(args):
        q = prof.get(path if len(path) == 1 else (path[0], '*'))
        if q is None:
            continue
        if _num(v) and q['ints']:
            lo = min(q['ints'])
            if (lo >= 1 and v < 1) or (lo >= 0 and v < 0):
                return False
        if _seq(v) and q['lens'] and len(v) < min(q['lens']):
            return False
        strings = [v] if type(v) is str else [x for x in v if type(x) is str] if type(v) in (list, tuple) else []
        if q['chars'] and any(not _chars(x) <= q['chars'] for x in strings):
            return False
    return True


def templates(seeds, consts_by_type, domain=True):
    """seeds: public base argument tuples. Returns candidates in a fixed order with template provenance.

    Every candidate is one edit of one seed at one position (minimal change). Within a type, seeds are interleaved so the
    per-type cap is shared. With domain=True, candidates outside the public-example domain profile are dropped."""
    prof = domain_profile(seeds)
    seen = {repr(s) for s in seeds}
    out = []
    # Degenerate inputs are labeled MISSING_CASE first; later types skip inputs already generated (global dedupe).
    for t in ('MISSING_CASE',) + TYPES[:-1]:
        consts = consts_by_type.get(t, [0, 1])
        streams = []
        for si, seed in enumerate(seeds):
            streams.append([(si, path, name, replace(seed, path, new)) for path, value in positions(seed)
                            for name, new in OPS[t](value, consts)
                            if type(new) is type(value) or (_num(value) and _num(new))])
        merged = [x for group in zip_longest(*streams) for x in group if x is not None]
        count = 0
        for si, path, name, cand in merged:
            if count >= MAX_PER_TYPE or len(out) >= MAX_TOTAL:
                break
            key = repr(cand)
            if key in seen or not ok_literal(cand) or (domain and not in_domain(cand, prof)):
                continue
            seen.add(key)
            where = f'argument {path[0] + 1}' + (f' element {path[1]}' if len(path) > 1 else '')
            out.append(dict(id=f'T{len(out)}', type=t, args=cand, template=f'{name} at {where} of public example {si + 1}'))
            count += 1
    return out


# ---- ranking and selection ----------------------------------------------------------------------------------------
def differs(a, b):
    """Observable difference between two execution outcomes ('ok', repr) / ('exception', type); timeouts never count."""
    if a is None or b is None or a[0] == 'timeout' or b[0] == 'timeout' or a[0] == 'skipped' or b[0] == 'skipped':
        return False
    return a != b


def rank(mutants, candidates, put_out, mutant_out, source_lines):
    """mutants: survivors with 'k', 'line', 'type', 'before', 'after'. put_out[i], mutant_out[k][i] per candidate.

    Concept = (line, fault type). Evidence: surviving alternatives at the site (the public tests cannot tell them from
    the PUT) that a template input on which the PUT returns normally distinguishes. Order: distinguished alternatives, then survivors, then fault-type
    priority, then line. No reference, spec or LLM enters the ranking."""
    groups = {}
    for m in mutants:
        g = groups.setdefault((m['line'], m['type']), dict(line=m['line'], type=m['type'], survivors=[], killed={}))
        g['survivors'].append(m)
        kills = [i for i in range(len(candidates)) if put_out[i] and put_out[i][0] == 'ok' and differs(put_out[i], mutant_out[m['k']][i])]
        if kills:
            g['killed'][m['k']] = kills
    rows = []
    for g in groups.values():
        rows.append(dict(g, distinguished=len(g['killed']), code=source_lines[g['line'] - 1].strip() if g['line'] <= len(source_lines) else ''))
    rows.sort(key=lambda g: (-g['distinguished'], -len(g['survivors']), PRIORITY[g['type']], g['line']))
    return rows


def select(groups, candidates, put_out, mutant_out, *, max_concepts=3, per_concept=2, max_inputs=6):
    """Top concepts on distinct lines with distinguishing inputs; fill with MISSING_CASE inputs (no alternative)."""
    chosen, concepts, lines = set(), [], set()
    for g in groups:
        if len(concepts) >= max_concepts or len(chosen) >= max_inputs:
            break
        if not g['distinguished'] or g['line'] in lines:
            continue
        score = {}
        for k, kills in g['killed'].items():
            for i in kills:
                score[i] = score.get(i, 0) + 1
        order = sorted(score, key=lambda i: (put_out[i][0] != 'ok', -score[i], candidates[i]['type'] != g['type'],
                                             len(repr(candidates[i]['args'])), i))
        picked = [i for i in order if i not in chosen][:min(per_concept, max_inputs - len(chosen))]
        if not picked:
            continue
        lines.add(g['line'])
        chosen.update(picked)
        alts = list(dict.fromkeys(f"`{m['before']}` -> `{m['after']}`" for m in g['survivors'] if m['k'] in g['killed']))[:3]
        rows = []
        for i in picked:
            k = next(k for k in g['killed'] if i in g['killed'][k])
            alt = next(m for m in g['survivors'] if m['k'] == k)
            rows.append(dict(index=i, alternative=f"`{alt['before']}` -> `{alt['after']}`", alternative_output=mutant_out[k][i]))
        concepts.append(dict(type=g['type'], line=g['line'], code=g['code'], alternatives=alts, survivors=len(g['survivors']),
                             distinguished=g['distinguished'], inputs=rows))
    missing = [i for i, c in enumerate(candidates) if c['type'] == 'MISSING_CASE' and i not in chosen and put_out[i] and put_out[i][0] == 'ok']
    fill = missing[:max_inputs - len(chosen)]
    if fill:
        chosen.update(fill)
        concepts.append(dict(type='MISSING_CASE', line=None, code=None, alternatives=[], survivors=0, distinguished=0,
                             inputs=[dict(index=i, alternative=None, alternative_output=None) for i in fill]))
    return concepts

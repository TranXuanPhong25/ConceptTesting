"""v47 (registered as v46) extended tool methods + LLM concept selection (see PREREG.md). Usage (repo root, PYTHONPATH=.):
  $V4_PYTHON .../v47_concept_select/select_run.py prepare     # tool side: instances + menus (no reference, no LLM)
  source <env with QWEN_BASE_URL>; $V4_PYTHON .../select_run.py generate   # LLM picks (menus only)
  $V4_PYTHON .../select_run.py score       # references enter only here
The endpoint URL comes from the environment only and is never written to disk or printed.
"""
import ast
import difflib
import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from trickcatcher_linefacts.analysis.v41_iorel import iorel
from trickcatcher_linefacts.analysis.v44_concept_matrix import matrix as M
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_concepts, ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import immutable
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_run import Reference, numbered
from trickcatcher_linefacts.pipelines.v34_ftplacebo.hypothesis_replay import freeze_local_constants

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v47_concept_select'
MODEL = 'qwen2.5-coder-32b-instruct'
K = 32
BASE = 40
MENU_MAX = 40
INPUT_KINDS = ('class', 'boundary', 'spec_range', 'value_biased', 'coverage', 'mutation')
CODE_KINDS = ('coverage', 'mutation')
ARMS = ('spec+code', 'spec-only')
MAXLEN = iorel.MAX_LEN


# ---- Part A: new tool methods (public examples + spec text only) ---------------------------------------------------
def log_uniform(rng, lo, hi):
    lo1 = max(lo, 1)
    if hi <= lo1:
        return hi
    v = int(round(math.exp(rng.uniform(math.log(lo1), math.log(hi)))))
    return min(max(v, lo), hi) if lo >= 1 else (v if rng.random() < 0.9 else lo)


def spec_range_members(case_id, xs, cons, pool_max):
    inst = {}
    for (i, kind), (lo, hi) in sorted(cons.items()):
        if hi <= pool_max:
            continue
        for variant in ('all', 'one'):
            rng = random.Random(f'{case_id}:{i}:{kind}:{variant}')
            name = f'arg{i}:{kind}_spread_{variant}'
            for x in xs[:BASE]:
                if i >= len(x):
                    continue
                v = x[i]
                if kind == 'elem' and type(v) is list and v and all(iorel.is_int(e) for e in v):
                    nv = [log_uniform(rng, lo, hi) for _ in v] if variant == 'all' else v[:-1] + [log_uniform(rng, lo, hi)]
                elif kind == 'elem2' and type(v) is list and v and all(type(r) is list and r and all(iorel.is_int(e) for e in r) for r in v):
                    nv = [[log_uniform(rng, lo, hi) for _ in r] for r in v] if variant == 'all' else [r[:] for r in v[:-1]] + [v[-1][:-1] + [log_uniform(rng, lo, hi)]]
                elif kind == 'value' and iorel.is_int(v) and variant == 'all':
                    nv = log_uniform(rng, lo, hi)
                else:
                    continue
                inst.setdefault(name, []).append(repr(x[:i] + (nv,) + x[i + 1:]))
    return {k: list(dict.fromkeys(v)) for k, v in inst.items()}


def value_biased_members(case_id, seeds, xs):
    inst = {}
    for i in range(len(seeds[0])):
        vals = [s[i] for s in seeds]
        if all(type(v) is list and all(iorel.is_int(e) for e in v) for v in vals) and any(vals):
            flat = [e for v in vals for e in v]
            lens = [len(v) for v in vals]
            grid = False
        elif all(type(v) is list and v and all(type(r) is list and all(iorel.is_int(e) for e in r) for r in v) for v in vals):
            flat = [e for v in vals for r in v for e in r]
            lens = [len(v) for v in vals]
            rowlens = [len(r) for v in vals for r in v]
            grid = True
        else:
            continue
        if not flat:
            continue
        lo, hi = min(flat), max(flat)
        for variant, p in (('only_public', 1.0), ('mostly_public', 0.7)):
            rng = random.Random(f'{case_id}:{i}:{variant}')
            name = f'arg{i}:{variant}_values'

            def elem():
                return rng.choice(flat) if rng.random() < p else rng.randint(lo, hi)
            for x in xs[:BASE]:
                n = rng.randint(min(lens), min(2 * max(lens), MAXLEN)) if max(lens) else 0
                if grid:
                    w = rng.choice(rowlens) if rowlens else 1
                    nv = [[elem() for _ in range(w)] for _ in range(max(n, 1))]
                else:
                    nv = [elem() for _ in range(n)]
                inst.setdefault(name, []).append(repr(x[:i] + (nv,) + x[i + 1:]))
    return {k: list(dict.fromkeys(v)) for k, v in inst.items()}


# ---- menus (tool-built descriptions) ---------------------------------------------------------------------------------
CLASS_TEXT = {'singleton': 'a single element', 'all_equal': 'all elements equal', 'many_duplicates': 'many duplicates (two values repeated)',
              'sorted_asc': 'sorted ascending', 'sorted_desc': 'sorted descending', 'strictly_increasing': 'strictly increasing, no duplicates',
              'contains_lower': 'contains the smallest allowed value', 'contains_upper': 'contains the largest allowed value',
              'longest': 'much longer than the examples', 'repeated_char': 'one character repeated', 'sorted_chars': 'characters sorted',
              'palindrome': 'a palindrome', 'single_char': 'a single character', 'lower': 'the smallest allowed value',
              'lower+1': 'the smallest allowed value + 1'}


def describe(kind, name, params, cons, mutant_text, case_id):
    m = re.match(r'arg(\d+):(.*)', name)
    p = params[int(m.group(1))] if m and int(m.group(1)) < len(params) else '?'
    tag = m.group(2) if m else name
    if kind == 'class':
        return f'{p}: {CLASS_TEXT.get(tag, tag)}'
    if kind == 'boundary':
        return f'{p}: {tag.replace("_", " ")} as allowed by the spec constraints'
    if kind == 'spec_range':
        return f'{p}: values spread over the full spec range ({tag.replace("_", " ")})'
    if kind == 'value_biased':
        return f'{p}: elements drawn {"only" if tag.startswith("only") else "mostly"} from values seen in the public examples'
    if kind == 'coverage':
        a, b = re.match(r'arc(-?\d+)->(-?\d+)', name).groups()
        return f'code path line {abs(int(a))} -> ' + (f'line {b}' if int(b) > 0 else 'function exit') + ', never taken by the public tests'
    return mutant_text.get(name, name)


def mutant_texts(case_id, names, masked):
    """Diff on the PUT source, displayed from the comment-masked view the model sees (same line count)."""
    job = json.loads((M.V34 / 'cases' / case_id / 'tool' / 'phase2' / 'job.json').read_text())
    put = job['sources']['put'].split('\n')
    shown = masked.split('\n')
    out = {}
    for n in names:
        src = job['sources'].get(n)
        if not src:
            continue
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, put, src.split('\n'), autojunk=False).get_opcodes():
            if tag != 'equal':
                before = ' '.join(shown[i1:i2]).strip()
                after = ' '.join(src.split('\n')[j1:j2]).strip()
                if '#' not in before:  # the masked view hides comments; hide them in the edited line too
                    after = after.split('#')[0].rstrip()
                before, after = before[:70], after[:70]
                out[n] = f'line {i1 + 1} written differently: `{before}` -> `{after}` (public tests cannot tell)'
                break
    return out


def menu(kinds, params, cons, mtext, case_id, arm):
    """Round-robin over kinds; an instance whose shown inputs equal an earlier item's is merged (first label kept)."""
    order = [k for k in INPUT_KINDS if arm == 'spec+code' or k not in CODE_KINDS]
    queues = {k: list(kinds[k]) for k in order}
    items, seen, merged = [], set(), 0
    while len(items) < MENU_MAX and any(queues.values()):
        for k in order:
            while queues[k] and len(items) < MENU_MAX:
                n = queues[k].pop(0)
                key = tuple(kinds[k][n]['flagged'][:K])
                if key in seen:
                    merged += 1
                    continue
                seen.add(key)
                items.append(dict(id=f'M{len(items) + 1}', kind=k, instance=n, text=describe(k, n, params, cons, mtext, case_id)))
                break
    return dict(items=items, merged=merged)


# ---- prepare (tool side) -----------------------------------------------------------------------------------------------
def prepare_case(case, run, v41_row):
    """Tool side only: PUT, public examples, spec text, frozen v41 pool inputs/PUT outcomes, v42_mutoracle mutant
    outcomes. No reference or contract is read here."""
    from trickcatcher_linefacts.analysis.v42_mutoracle import mutoracle
    inputs, put = mutoracle.load_pool(case['case_id'], v41_row)
    seeds = ft_run.base_inputs(case, 'vibepass_half')
    domain = ft_concepts.domain_profile(seeds)
    prof = iorel.profile(seeds)
    xs = [x for x in iorel.sample(seeds) if ft_concepts.in_domain(x, domain)]
    if any(repr(x) not in set(inputs) for x in xs):
        raise RuntimeError('resampled inputs are not in the frozen v41 pool')
    task = run.task(case)
    params = M.param_names(task['signature'])
    cons = M.constraints(task['spec'], params)
    pool_max = max((_maxabs(l)['maxabs'] for l in inputs), default=0)
    builders = {'class': lambda: M.class_members(xs, prof, cons, seeds), 'boundary': lambda: M.boundary_members(xs, cons),
                'coverage': lambda: M.coverage_arcs(case, seeds, inputs), 'mutation': lambda: M.mutation(case, inputs, put),
                'spec_range': lambda: spec_range_members(case['case_id'], xs, cons, pool_max),
                'value_biased': lambda: value_biased_members(case['case_id'], seeds, xs)}
    kinds, errors = {}, {}
    for k, build in builders.items():
        try:
            kinds[k] = M.dedupe(build())
        except Exception as exc:  # per kind, not fatal
            errors[k] = f'{type(exc).__name__}: {exc}'[:300]
            kinds[k] = {}
    mtext = mutant_texts(case['case_id'], list(kinds['mutation']), task['source_masked'])
    menus = {arm: menu(kinds, params, cons, mtext, case['case_id'], arm) for arm in ARMS}
    universes = {k: list(dict.fromkeys(l for v in kinds[k].values() for l in v['flagged'])) for k in ('class', 'boundary', 'spec_range', 'value_biased')}
    return dict(case_id=case['case_id'], errors=errors, kinds={k: {n: v['flagged'][:K] for n, v in d.items()} for k, d in kinds.items()},
                menus=menus, pool_max=pool_max, universes=universes)


def _maxabs(lit):
    best = 0
    stack = [ast.literal_eval(lit)]
    while stack:
        v = stack.pop()
        if type(v) in (list, tuple):
            stack.extend(v)
        elif type(v) is int:
            best = max(best, abs(v))
    return dict(maxabs=best)


def prompt(task, case, items, arm):
    ctx = dict(signature=task['signature'], spec=task['spec'], public_tests=task['base'])
    if arm == 'spec+code':
        ctx['code'] = numbered(task)
    instr = ('The code passes its public tests but may be wrong on other inputs. Below is a menu of test ideas (input '
             'classes, spec boundaries, value patterns' + (', untested code paths, plausible small code changes' if arm == 'spec+code' else '') +
             '). Pick the 3 ideas most likely to produce an input on which the code returns a result that disagrees with '
             'the spec. Reply with JSON {"picks": ["M..", "M..", "M.."], "reasons": ["...", "...", "..."]}.')
    return [{'role': 'system', 'content': 'Return exactly one JSON object. No Markdown.'},
            {'role': 'user', 'content': json.dumps(dict(instruction=instr, context=ctx,
                                                        menu=[f"{it['id']}: {it['text']}" for it in items]), ensure_ascii=False)}]


def parse_picks(text, items):
    ids = {it['id'] for it in items}
    try:
        v = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text or '', re.S)
        try:
            v = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            v = {}
    raw = v.get('picks') if isinstance(v, dict) else None
    if isinstance(raw, list):
        cand = [f'M{p}' if isinstance(p, int) else (re.search(r'\bM(\d+)\b', str(p), re.I) and 'M' + re.search(r'\bM(\d+)\b', str(p), re.I).group(1)) for p in raw]
    else:  # string picks, or truncated / unparseable JSON: ids from the picks segment
        seg = str(raw) if raw is not None else (text or '').split('reasons')[0]
        cand = ['M' + m for m in re.findall(r'\bM(\d+)\b', seg, re.I)]
    picks = []
    for p in cand:
        if p in ids and p not in picks:
            picks.append(p)
    return picks[:3]


def main():
    cmd = sys.argv[1]
    freeze_local_constants()
    run = ft_run.FTRun('vibepass_half')
    cases = run.cases
    prep_path = OUT / 'prepared.json'
    if cmd == 'prepare':
        v41 = {r['case_id']: r for r in json.loads((iorel.OUT / 'ceiling.json').read_text())['rows']}

        def safe(case):
            try:
                return prepare_case(case, run, v41[case['case_id']])
            except Exception as exc:
                return dict(case_id=case['case_id'], error=f'{type(exc).__name__}: {exc}'[:300])
        with ThreadPoolExecutor(6) as pool:
            prepared = {p['case_id']: p for p in pool.map(safe, cases)}
        OUT.mkdir(parents=True, exist_ok=True)
        immutable(prep_path, prepared)
        print({cid: (p.get('error') or {a: len(p['menus'][a]['items']) for a in ARMS}) for cid, p in list(prepared.items())[:6]})
        return
    prepared = json.loads(prep_path.read_text())
    if cmd == 'generate':
        import openai
        client = openai.OpenAI(base_url=os.environ['QWEN_BASE_URL'], api_key='none', timeout=3600, max_retries=3,
                               default_headers={'ngrok-skip-browser-warning': '1'})

        def call(job):
            case, arm = job
            p = prepared[case['case_id']]
            path = OUT / 'calls' / case['case_id'] / f'{arm}.json'
            if 'error' in p or not p['menus'][arm]['items']:
                return case['case_id'], arm, 'skipped'
            if path.exists():
                return case['case_id'], arm, 'cached'
            msgs = prompt(run.task(case), case, p['menus'][arm]['items'], arm)
            r = client.chat.completions.create(model=MODEL, messages=msgs, temperature=0,
                                               max_tokens=512, seed=20261022, response_format={'type': 'json_object'})
            immutable(path, dict(text=r.choices[0].message.content or '', finish_reason=r.choices[0].finish_reason,
                                 input_tokens=r.usage.prompt_tokens, output_tokens=r.usage.completion_tokens,
                                 prompt_sha256=hashlib.sha256(json.dumps(msgs, sort_keys=True).encode()).hexdigest()))
            return case['case_id'], arm, r.choices[0].finish_reason
        with ThreadPoolExecutor(1) as pool:
            for res in pool.map(call, [(c, a) for c in cases for a in ARMS]):
                print(*res)
        return
    score(run, cases, prepared)


# ---- score (references only here) ------------------------------------------------------------------------------------
def poisson_binomial_tail(ps, x):
    dist = [1.0]
    for p in ps:
        dist = [a * (1 - p) + (dist[i - 1] * p if i else 0.0) for i, a in enumerate(dist + [0.0])]
    return sum(dist[x:])


def p_any(m, h, c):
    """Chance that c distinct random items out of m (h covering) include a covering one."""
    if c <= 0 or h <= 0:
        return 0.0
    if m - h < c:
        return 1.0
    return 1 - math.comb(m - h, c) / math.comb(m, c)


def score(run, cases, prepared):
    official = Reference(run)
    official.root = iorel.OUT / 'official'
    v41 = {r['case_id']: r for r in json.loads((iorel.OUT / 'ceiling.json').read_text())['rows']}
    v44 = {r['case_id']: r for r in json.loads((M.OUT / 'matrix.json').read_text())['rows']}
    missing = [(c['case_id'], a) for c in cases for a in ARMS if 'error' not in prepared[c['case_id']]
               and prepared[c['case_id']]['menus'][a]['items'] and not (OUT / 'calls' / c['case_id'] / f'{a}.json').exists()]
    if missing:
        raise SystemExit(f'{len(missing)} call records missing; run generate first (nothing written)')
    rows, missing = [], 0
    for case in cases:
        cid = case['case_id']
        p = prepared[cid]
        if 'error' in p:
            rows.append(dict(case_id=cid, error=p['error']))
            continue
        try:
            inputs, put, rr = M.load_pool(case, v41[cid])
            pool_exp, _ = M.exposing_set(inputs, put, rr['contract'], rr['ref'])
            exp, universes, skipped = set(pool_exp), {}, {}
            ref = case['reference']
            for k in ('class', 'boundary', 'spec_range', 'value_biased'):  # one batch per generated kind
                U = p['universes'][k]  # all flagged inputs of the kind (v44 universe), not only the shown 32
                universes[k] = U
                new = sorted(set(U) - set(inputs))
                if new:
                    d = OUT / 'cases' / cid / 'generated' / k
                    gp = iorel.run_batch(d / 'put', {'put': case['source']}, case['entry'], new)['put']
                    gr = iorel.run_batch(d / 'ref', {'contract': ref['contract'], 'ref': ref['source']}, ref['entry'], new)
                    e2, _ = M.exposing_set(new, gp, gr['contract'], gr['ref'])
                    exp |= e2
                    skipped[k] = sum(o[0] == 'skipped' for o in gp) + sum(o[0] == 'skipped' for o in gr['ref'])
            for k in ('coverage', 'mutation'):
                universes[k] = list(inputs)
            memo = {}

            def confirmed(lit):
                if lit not in memo:
                    memo[lit] = lit in exp and iorel.official_exposes(official, case, lit)
                return memo[lit]
            cover = {(k, n): any(confirmed(l) for l in shown if l in exp) for k, d in p['kinds'].items() for n, shown in d.items()}
            partA = {}
            for k in INPUT_KINDS:
                inst = p['kinds'][k]
                if not inst:
                    partA[k] = dict(applicable=False)
                    continue
                U = set(universes[k])
                R = {l for v in inst.values() for l in v}
                eU = len(exp & U)
                partA[k] = dict(applicable=True, covered=any(cover[(k, n)] for n in inst),
                                matched_random=round(iorel.random_k(len(U), eU, len(R & U)), 4),
                                random_instance_batch=round(statistics.mean(bool(set(v) & exp) for v in inst.values()), 4))
            union4 = any(partA[k].get('covered') for k in ('class', 'boundary', 'coverage', 'mutation'))
            union6 = any(partA[k].get('covered') for k in INPUT_KINDS)
            c1 = union6 or any(confirmed(l) for l in sorted(pool_exp)[:20])
            repro = {k: partA[k].get('covered', False) == v44[cid][k].get('covered', False) for k in ('class', 'boundary', 'coverage', 'mutation')}
            row = dict(case_id=cid, partA=partA, union4=union4, union6=union6, c1=c1, v44_reproduced=all(repro.values()),
                       generated_skipped=skipped, perfect_all_instances=any(cover.values()))
            for arm in ARMS:
                items = p['menus'][arm]['items']
                path = OUT / 'calls' / cid / f'{arm}.json'
                rec = json.loads(path.read_text()) if path.exists() else None
                missing += rec is None and bool(items)
                picks = parse_picks(rec['text'], items) if rec else []
                byid = {it['id']: it for it in items}
                cov = {it['id']: cover[(it['kind'], it['instance'])] for it in items}
                m, h = len(items), sum(cov.values())
                kinds_in = {}
                for it in items:
                    kinds_in.setdefault(it['kind'], []).append(cov[it['id']])
                # one random instance from each of 3 random distinct kinds (exact)
                triples = list(itertools.combinations(sorted(kinds_in), min(3, len(kinds_in))))
                per_kind = statistics.mean(1 - math.prod(1 - sum(kinds_in[k]) / len(kinds_in[k]) for k in t) for t in triples) if triples else 0.0
                # random instances of the same kinds the model picked
                picked_kinds = {}
                for i in picks:
                    picked_kinds[byid[i]['kind']] = picked_kinds.get(byid[i]['kind'], 0) + 1
                kind_matched = 1 - math.prod(1 - p_any(len(kinds_in[k]), sum(kinds_in[k]), c) for k, c in picked_kinds.items()) if picks else 0.0
                row[arm] = dict(menu=m, merged=p['menus'][arm]['merged'], menu_covering=h, perfect=h > 0, random3=round(p_any(m, h, 3), 4),
                                first3=any(cov[it['id']] for it in items[:3]), per_kind_random3=round(per_kind, 4),
                                kind_matched_random=round(kind_matched, 4), picks=picks, parsed=bool(picks),
                                covered3=any(cov[i] for i in picks), pick_kinds=[byid[i]['kind'] for i in picks],
                                finish=rec and rec['finish_reason'])
            rows.append(row)
        except Exception as exc:  # per case, recorded
            rows.append(dict(case_id=cid, error=f'score: {type(exc).__name__}: {exc}'[:300]))
    ok = [r for r in rows if 'error' not in r]
    partA = {k: dict(applicable=sum(r['partA'][k]['applicable'] for r in ok), ideal=sum(r['partA'][k].get('covered', False) for r in ok),
                     matched_random=round(sum(r['partA'][k].get('matched_random', 0) for r in ok), 2),
                     random_instance_batch=round(sum(r['partA'][k].get('random_instance_batch', 0) for r in ok), 2)) for k in INPUT_KINDS}
    partB = {}
    for arm in ARMS:
        a = [r[arm] for r in ok]
        kc = {}
        for x in a:
            for k in x['pick_kinds']:
                kc[k] = kc.get(k, 0) + 1
        cov3 = sum(x['covered3'] for x in a)
        partB[arm] = dict(covered3=cov3, random3=round(sum(x['random3'] for x in a), 2),
                          p_value_vs_random3=round(poisson_binomial_tail([x['random3'] for x in a], cov3), 4),
                          first3=sum(x['first3'] for x in a), per_kind_random3=round(sum(x['per_kind_random3'] for x in a), 2),
                          kind_matched_random=round(sum(x['kind_matched_random'] for x in a), 2),
                          perfect_menu=sum(x['perfect'] for x in a), parsed=sum(x['parsed'] for x in a),
                          merged=sum(x['merged'] for x in a), pick_kinds=kc)
    b = partB['spec+code']
    verdict = 'incomplete' if missing or len(ok) < len(rows) else (
        'promising' if b['covered3'] >= b['random3'] + 3 and b['covered3'] >= 0.5 * b['perfect_menu'] else 'no-go')
    summary = dict(n=len(rows), errors=len(rows) - len(ok), missing_calls=missing,
                   partA_exploratory=dict(per_kind=partA, union4=sum(r['union4'] for r in ok), union4_v44=21,
                                          union6=sum(r['union6'] for r in ok), c1=sum(r['c1'] for r in ok), c1_v44=22,
                                          v44_reproduced_tasks=sum(r['v44_reproduced'] for r in ok),
                                          perfect_all_instances=sum(r['perfect_all_instances'] for r in ok),
                                          generated_skipped=sum(sum(r['generated_skipped'].values()) for r in ok)),
                   partB=partB, verdict=verdict)
    if verdict == 'incomplete':  # never freeze a partial result
        (OUT / 'score_incomplete.json').write_text(json.dumps(dict(summary=summary, rows=rows), indent=1) + '\n')
    else:
        immutable(OUT / 'score.json', dict(summary=summary, rows=rows))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()

"""v61: interpretation concept before a definitional oracle, Qwen writer (see PREREG.md). Repo root, PYTHONPATH=.:
  source <env with QWEN_BASE_URL>; $V4_PYTHON .../v61_qwen_interpretation/run.py generate   # 1 worker, resumable
  $V4_PYTHON .../v61_qwen_interpretation/run.py freeze
  $V4_PYTHON .../v61_qwen_interpretation/run.py score                                      # references only here
The endpoint URL comes from the environment only; it is never written or printed.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from trickcatcher_linefacts.analysis.v46_mutoracle_fixed.oracle import complete, digest
from trickcatcher_linefacts.analysis.v49_defn_oracle import gen
from trickcatcher_linefacts.analysis.v49_defn_oracle import oracle as O
from trickcatcher_linefacts.analysis.v53_validity_smallscope import smallscope as S
from trickcatcher_linefacts.analysis.v53_validity_smallscope import validity as V
from trickcatcher_linefacts.analysis.v59_blind_concept import run as B
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import immutable

E = O.E
HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v61_qwen_interpretation'
B.OUT = OUT  # v59 helpers (accept, truth_for) write under this experiment's root
MODEL = gen.MODEL
FAMILIES = ('defn', 'interp', 'placebo')
NPROG = gen.NPROG
PREFIX = {
    'interp': ('First list in comments every ambiguity in the problem statement (`# AMBIGUITY:` lines), then choose the '
               'interpretation that agrees with every public example and state it in one `# INTERPRETATION:` comment. '),
    'placebo': 'First write an 80-120 word comment block on the code formatting conventions you will follow. ',
}


def tasks():
    run, probs = V.problems()
    pid_of = {c['case_id']: p for p, cs in probs.items() for c in cs}
    return run, probs, {c['case_id']: c for c in run.cases}, pid_of


def messages(case, fam):
    system, user = gen.messages(E.task_view(case), 'defn')
    assert user['content'].endswith(gen.INSTR['defn'])
    content = user['content'][:-len(gen.INSTR['defn'])] + PREFIX[fam] + gen.INSTR['defn']
    return [system, dict(user, content=content)]


def params(cid, fam, i):
    seed = int(hashlib.sha256(f'v61/{cid}/{fam}/{i}'.encode()).hexdigest()[:8], 16)
    return dict(seed=seed, temperature=0.8, top_p=0.95, max_tokens=1024)


def generate():
    import openai
    client = openai.OpenAI(base_url=os.environ['QWEN_BASE_URL'], api_key='none', timeout=900, max_retries=2,
                           default_headers={'ngrok-skip-browser-warning': '1'})
    served = {m.id: getattr(m, 'max_model_len', None) for m in client.models.list().data}
    if served.get(MODEL, 0) != 8192:
        raise SystemExit(f'{MODEL} not served with max_model_len 8192')
    _, _, cs, _ = tasks()
    errors = 0
    for i in range(NPROG):  # sample-major: an endpoint loss leaves every task with the same number of programs
        for fam in ('interp', 'placebo'):
            for cid in sorted(cs, key=int):
                path, msgs, p = OUT / 'programs' / fam / cid / f'{i}.json', messages(cs[cid], fam), params(cid, fam, i)
                try:
                    complete(client, path, msgs, **p)
                except openai.BadRequestError as exc:
                    if 'context' not in str(exc).lower():
                        errors += 1
                        print('BadRequestError', path.relative_to(OUT), str(exc)[:120], flush=True)
                        continue
                    immutable(path, dict(text='', finish_reason='context_overflow', input_tokens=None, output_tokens=0,
                                         digest=digest(msgs, p)))
                except Exception as exc:  # recorded; a rerun resumes from the cache
                    errors += 1
                    print(type(exc).__name__, path.relative_to(OUT), str(exc)[:120], flush=True)
        print('sample', i, 'errors so far', errors, flush=True)
    print('done', 'errors', errors, flush=True)
    if errors:
        raise SystemExit(1)


def sources(inv, case, fam):
    """Five program sources ('' = missing/overflow/unparsable) and finish reasons."""
    cid = case['case_id']
    if fam == 'defn':
        loaded = O.programs(inv, case, 'defn', set())
        return [loaded['sources'].get(i, '') for i in range(NPROG)], loaded['finish_reason']
    srcs, finish = [], {}
    for i in range(NPROG):
        rec = json.loads((OUT / 'programs' / fam / cid / f'{i}.json').read_text())
        if rec['digest'] != digest(messages(case, fam), params(cid, fam, i)):
            raise SystemExit(f'prompt digest differs: {fam}/{cid}/{i}')
        finish[str(i)] = rec['finish_reason']
        srcs.append('' if rec['finish_reason'] == 'context_overflow' else (O.code_block(rec['text']) or ''))
    return srcs, finish


def external_files():
    """Everything outside this folder that `score` reads (Amendment 1, Codex M1): v49 defn programs and task records
    (PUT outcomes, universe), v41 PUT/reference caches, Stage 1 open checks, and the helper sources."""
    _, probs, cs, _ = tasks()
    files = [O.OUT / 'programs' / 'defn' / cid / f'{i}.json' for cid in cs for i in range(NPROG)]
    files += [O.OUT / 'tasks' / f'{cid}.json' for cid in cs]
    files += sorted(p for cid in cs for p in (E.iorel.OUT / 'cases' / cid).rglob('*.json'))
    files += [V.OUT / 'answers' / f'{pid}_open.txt' for pid in probs]
    files += [Path(m.__file__) for m in (O, gen, S, V, B, E, E.iorel)]
    return files


def frozen_state():
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return dict(programs={str(p.relative_to(OUT)): sha(p) for p in sorted((OUT / 'programs').rglob('*.json'))},
                sources={f: sha(HERE / f) for f in ('run.py', 'PREREG.md')},
                external={str(p.relative_to(HERE.parents[2])): sha(p) for p in external_files()})


def freeze():
    _, _, cs, _ = tasks()
    missing = [f'{f}/{c}/{i}' for f in ('interp', 'placebo') for c in cs for i in range(NPROG)
               if not (OUT / 'programs' / f / c / f'{i}.json').is_file()]
    state = frozen_state()
    absent = [n for n, h in state['external'].items() if h is None]
    if missing or absent:
        raise SystemExit(f'incomplete: {len(missing)} programs missing {missing[:3]}; external absent {absent[:3]}')
    for f in ('interp', 'placebo'):  # schema + prompt digest preflight
        for c in cs:
            sources(None, cs[c], f)
    O.immutable(OUT / 'frozen.json', state)
    print('frozen')


def family_rows(case, rec, fam, srcs, inputs):
    with E.execution_root(OUT):
        base = O.run_programs(case, fam, srcs, rec['base_inputs'], 'base', 2)
        reasons = {j: O.rejection(rec['base_put'], base[f'p{j}']) if srcs[j] else 'missing' for j in range(NPROG)}
        strict = [j for j in range(NPROG) if srcs[j] and not reasons[j]]
        tolerant = [j for j in range(NPROG) if srcs[j] and (not reasons[j] or (
            O.resource_only(reasons[j], base[f'p{j}']) and 'mismatch' not in reasons[j]
            and any(o and o[0] == 'ok' for o in base[f'p{j}'])))]
        ran = O.run_programs(case, f'{fam}_valid', [srcs[j] for j in tolerant], inputs, 'universe') if inputs and tolerant else {}
    rows = {}
    for name, ids in (('tolerant', tolerant), ('strict', strict)):
        rows[name] = {}
        for n, l in enumerate(inputs):
            outs = [ran[f'p{tolerant.index(j)}'][n] for j in ids]
            put = rec['inputs'][l]['put']
            rows[name][l] = dict(put=put, programs=outs, **O.votes(put, outs))
    return rows, strict, tolerant


def common_mode(inputs, rows, truth):
    """Valid exposing inputs where >= 2 finishing valid programs all return one incorrect value (miss: = PUT; fa: != PUT)."""
    miss = fa = 0
    for l in inputs:
        t, row = truth[l], rows[l]
        put = E.iorel.value(row['put'])
        if not (t['valid'] and t['ref'] is not None and put is not None and not E.same(put, t['ref'])):
            continue
        vals = [E.iorel.value(o) for o in row['programs'] if o and o[0] == 'ok']
        vals = [v for v in vals if v is not None]
        if len(vals) >= 2 and all(E.same(v, vals[0]) for v in vals) and not E.same(vals[0], t['ref']) and t['exposes']():
            miss += E.same(vals[0], put)
            fa += not E.same(vals[0], put)
    return dict(miss=miss, fa=fa)


def score():
    frozen = json.loads((OUT / 'frozen.json').read_text())
    now = frozen_state()
    changed = sorted(f for f in frozen if frozen[f] != now[f])
    if changed:
        raise SystemExit(f'frozen state changed: {changed}')
    inv = O.Inventory()
    _, ready = O.score_inputs(inv)
    _, _, records, _ = ready
    run, probs, cs, pid_of = tasks()
    official = E.Reference(run)
    official.root = OUT / 'references' / 'official'
    res = {}
    for cid in sorted(cs, key=int):
        case, rec, pid = cs[cid], records[cid], pid_of[cid]
        universe = E.ordered(rec['inputs'])
        acc = B.accept(case, rec, pid, universe)
        inputs = [l for l in universe if acc[l]]
        view = {l: dict(put=rec['inputs'][l]['put']) for l in inputs}
        truth = B.truth_for(inv, case, view, official)
        res[cid] = dict(problem=pid, inputs=len(inputs), families={})
        for fam in FAMILIES:
            srcs, finish = sources(inv, case, fam)
            rows, strict, tolerant = family_rows(case, rec, fam, srcs, inputs)
            m = S.arm_metrics(inputs, rows, truth, len(tolerant), len(strict))
            m.update(valid=len(tolerant), strict_valid=len(strict), finish=finish,
                     common_mode=common_mode(inputs, rows['tolerant'], truth))
            res[cid]['families'][fam] = m
        print(cid, {f: (m['valid'], m['confirmed_tasks'], m['fa_tests'], m['common_mode']) for f, m in res[cid]['families'].items()},
              flush=True)
    tot = lambda f, k: sum(t['families'][f][k] for t in res.values())
    totals = {f: dict(confirmed_tasks=tot(f, 'confirmed_tasks'), confirmed_tests=tot(f, 'confirmed_tests'),
                      tests=tot(f, 'tests'), fa_tests=tot(f, 'fa_tests'), valid=tot(f, 'valid'), reach=tot(f, 'reach'),
                      strict_confirmed_tasks=sum(t['families'][f]['strict']['confirmed_tasks'] for t in res.values()),
                      common_mode_problems=len({t['problem'] for t in res.values()
                                                if sum(t['families'][f]['common_mode'].values())}))
              for f in FAMILIES}
    for t in totals.values():
        t['precision'] = t['confirmed_tests'] / t['tests'] if t['tests'] else None
    checks = {}
    for comp in ('defn', 'placebo'):
        net = {}
        for t in res.values():
            net[t['problem']] = net.get(t['problem'], 0) + t['families']['interp']['confirmed_tasks'] - t['families'][comp]['confirmed_tasks']
        checks[comp] = dict(margin=totals['interp']['confirmed_tasks'] - totals[comp]['confirmed_tasks'],
                            positive_problems=sorted(p[:12] for p, v in net.items() if v > 0),
                            fewer_common_mode=totals['interp']['common_mode_problems'] < totals[comp]['common_mode_problems'])
        checks[comp]['ok'] = (checks[comp]['margin'] >= 2 and len(checks[comp]['positive_problems']) >= 2
                              and checks[comp]['fewer_common_mode'])
    fa_ok = totals['interp']['fa_tests'] <= min(totals['defn']['fa_tests'], totals['placebo']['fa_tests'])
    verdict = 'promising' if fa_ok and all(c['ok'] for c in checks.values()) else 'no-go'
    usage = {}  # Amendment 1 (Codex S2): requested-equal budget, actual usage reported
    for fam in FAMILIES:
        root = O.OUT if fam == 'defn' else OUT
        recs = [json.loads(p.read_text()) for p in sorted((root / 'programs' / fam).rglob('*.json'))]
        usage[fam] = dict(output_tokens=sum(r.get('output_tokens') or 0 for r in recs),
                          finish={k: sum(r['finish_reason'] == k for r in recs) for k in {r['finish_reason'] for r in recs}})
    if frozen_state() != frozen:  # Amendment 1 (Codex M1): nothing changed while scoring
        raise SystemExit('frozen state changed during score')
    out = dict(verdict=verdict, checks=checks, fa_ok=fa_ok, totals=totals, usage=usage, tasks=res,
               frozen_sha256=hashlib.sha256((OUT / 'frozen.json').read_bytes()).hexdigest())
    O.immutable(OUT / 'score.json', out)
    print(json.dumps({k: out[k] for k in ('verdict', 'checks', 'fa_ok', 'totals', 'usage')}, indent=1))


if __name__ == '__main__':
    raise SystemExit(dict(generate=generate, freeze=freeze, score=score)[sys.argv[1]]() or 0)

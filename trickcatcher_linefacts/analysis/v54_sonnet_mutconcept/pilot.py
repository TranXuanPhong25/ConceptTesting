"""v54 pilot (ex-v53_sonnet_mutconcept): v46 TC variants (tc vs tc_concept) written by Claude Sonnet subagents (see PREREG.md). Usage (repo root):
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v54_sonnet_mutconcept/pilot.py prompts   # v46 prompts -> prompt files
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v54_sonnet_mutconcept/pilot.py audit     # agents.json -> runs.json
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v54_sonnet_mutconcept/pilot.py score     # Sonnet arms
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v54_sonnet_mutconcept/pilot.py qwen      # after v46 score only
Sonnet replies are written by subagents to out/.../programs/<arm>/<task>/<i>.txt. agents.json maps `<arm>/<task>/<i>` to
the subagent's transcript; audit keeps a program only if the subagent made exactly one Read of its prompt file and one
Write of its answer file (plus the hand-back).
"""
import collections
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from trickcatcher_linefacts import tc_full
from trickcatcher_linefacts.analysis.v41_iorel import iorel
from trickcatcher_linefacts.analysis.v42_mutoracle import mutoracle
from trickcatcher_linefacts.analysis.v46_mutoracle_fixed import oracle as O
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_run import Reference, same

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v54_sonnet_mutconcept'
TASKS = ('85', '141', '46', '65', '101', '161')
ARMS = ('tc', 'tc_concept')
K = 3
HANDBACK = ('SubagentHandback',)


def material():
    run = ft_run.FTRun('vibepass_half')
    by_case = collections.defaultdict(list)
    for q in O.load_questions():
        by_case[q['case_id']].append(q)
    return run, {c['case_id']: c for c in run.cases}, by_case


def prompt_path(cid, arm):
    return OUT / 'prompts' / f'{cid}_{arm}.txt'


def answer_path(key):
    arm, cid, i = key.split('/')
    return OUT / 'programs' / arm / cid / f'{i}.txt'


def prompts():
    run, cases, by_case = material()
    templates = tc_full.templates()
    for cid in TASKS:
        cs = O.concepts(cases[cid], by_case[cid])
        for arm in ARMS:
            msgs = O.tc_messages(cases[cid], arm, cs, templates)
            seed = int(hashlib.sha256(f'v46/{cid}/{arm}/0'.encode()).hexdigest()[:8], 16)
            rec = json.loads((O.OUT / 'programs' / arm / cid / '0.json').read_text())
            if rec['digest'] != O.digest(msgs, dict(seed=seed, **tc_full.PARAMS)):
                raise SystemExit(f'{cid} {arm}: prompt differs from the v46 Qwen call')
            path = prompt_path(cid, arm)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"SYSTEM:\n{msgs[0]['content']}\n\nUSER:\n{msgs[1]['content']}\n")
    print('prompts', len(TASKS) * len(ARMS), OUT / 'prompts')


def audit():
    """Tool calls and model per subagent transcript (JSONL); a program is clean iff the only tools are one Read of its
    prompt and one Write of its answer (the hand-back aside)."""
    agents = json.loads((OUT / 'agents.json').read_text())
    runs = {}
    for key, transcript in sorted(agents.items()):
        arm, cid, _ = key.split('/')
        tools, models = [], set()
        for line in Path(transcript).read_text().splitlines():
            msg = json.loads(line).get('message') or {}
            if msg.get('role') != 'assistant':
                continue
            models.add(msg.get('model'))
            for c in msg.get('content') or []:
                if isinstance(c, dict) and c.get('type') == 'tool_use':
                    path = (c.get('input') or {}).get('file_path')  # transcripts predate the v53 -> v54 renumber
                    tools.append([c['name'], path.replace('/v53_sonnet_mutconcept/', '/v54_sonnet_mutconcept/') if path else path])
        core = [t for t in tools if t[0] not in HANDBACK]
        strict = core == [['Read', str(prompt_path(cid, arm))], ['Write', str(answer_path(key))]]
        # amendment 2 (leakage rule): one Read of its prompt, then only Write/Edit of its own answer file
        clean = (core[:1] == [['Read', str(prompt_path(cid, arm))]] and len(core) >= 2 and core[1][0] == 'Write'
                 and all(t[0] in ('Write', 'Edit') and t[1] == str(answer_path(key)) for t in core[1:]))
        runs[key] = dict(tools=tools, models=sorted(m for m in models if m), clean=clean, strict=strict)
    (OUT / 'runs.json').write_text(json.dumps(runs, indent=1) + '\n')
    print('audited', len(runs), 'clean', sum(r['clean'] for r in runs.values()), 'strict', sum(r['strict'] for r in runs.values()),
          'models', sorted({m for r in runs.values() for m in r['models']}))


def sonnet_programs(cid, arm, runs, excluded, rule='clean'):
    srcs, texts = [], []
    for i in range(K):
        key, p = f'{arm}/{cid}/{i}', answer_path(f'{arm}/{cid}/{i}')
        if not runs[key][rule] or not p.exists():  # KeyError on an unaudited program: fail loudly
            excluded.append(key)
            srcs.append('')
            texts.append('')
        else:
            texts.append(p.read_text())
            srcs.append(tc_full.source(texts[-1]))
    return srcs


def shown_edits(cq):
    """(line, before, after) keys of the concept block, as O.concepts builds it (distinct, package order, <= 5)."""
    keys = []
    for q in cq:
        key = (q['line'], q['before'], q['after'])
        if key not in keys:
            keys.append(key)
    return keys[:O.MAX_CONCEPTS]


def applies_edit(case, cs, src):
    """Approximate: some program line equals a shown concept line with its `before` -> `after` edit applied."""
    lines = {ln.strip() for ln in src.split('\n')}
    return any(c['code_line'] and c['before'] in c['code_line']
               and c['code_line'].replace(c['before'], c['after'], 1).strip() in lines for c in cs)


def execute(case, srcs, inputs, d):
    """v46 run_programs with this pilot's cache dir: one process; on a crash one per program, a lone crash is skipped."""
    names = [f'p{i}' for i in range(len(srcs))]
    if not names:
        return {}
    sources = {n: O.program_module(case, s) for n, s in zip(names, srcs)}
    try:
        return O.batch(d, sources, names, case['entry'], inputs)
    except RuntimeError:
        out = {}
        for n in names:
            try:
                out.update(O.batch(d / n, sources, [n], case['entry'], inputs))
            except RuntimeError:
                out[n] = [['skipped']] * len(inputs)
        return out


class Scorer:
    def __init__(self):
        self.run, self.cases, self.by_case = material()
        self.official = Reference(self.run)
        self.official.root = iorel.OUT / 'official'
        self.truth, self.confirmed_cache = {}, {}
        for cid in TASKS:
            inputs = json.loads((iorel.OUT / 'cases' / cid / 'put' / 'job.json').read_text())['inputs']
            put_raw = json.loads((iorel.OUT / 'cases' / cid / 'put' / 'result.json').read_text())['put']
            self.truth[cid] = (inputs, mutoracle.load_ref(self.cases[cid], inputs), put_raw)

    def judge_test(self, cid, k, value):  # = v46 score.judge_test
        inputs, res, put_raw = self.truth[cid]
        ref = iorel.value(res['ref'][k])
        if res['contract'][k][0] != 'ok' or ref is None or value is None or not same(value, ref):
            return 'fa'
        if (cid, k) not in self.confirmed_cache:
            put = iorel.value(put_raw[k])
            self.confirmed_cache[(cid, k)] = put is not None and not same(put, ref) and iorel.official_exposes(
                self.official, self.cases[cid], inputs[k])
        return 'confirmed' if self.confirmed_cache[(cid, k)] else 'unconfirmed'

    def task_facts(self, cid):
        """Exposing question inputs (reference value confirmed) and whether a D1 edit is among the shown concepts."""
        cq, res = self.by_case[cid], self.truth[cid][1]
        ks = sorted({q['k'] for q in cq})
        exposing = [k for k in ks if self.judge_test(cid, k, iorel.value(res['ref'][k])) == 'confirmed']
        d1 = {(q['line'], q['before'], q['after']) for q in cq
              if self.judge_test(cid, q['k'], iorel.value(q['mut'])) == 'confirmed'}
        return dict(exposing=exposing, d1_edits=len(d1), d1_shown=bool(d1 & set(shown_edits(cq))))

    def evaluate(self, case, srcs, tag):
        """v46 program-arm oracle on one task: validity on the public base inputs, tc-full vote on the question inputs;
        plus the program-level secondary (valid program = reference on every exposing question input)."""
        cid, cq = case['case_id'], self.by_case[case['case_id']]
        d = OUT / 'exec' / cid
        seeds = [repr(x) for x in ft_run.base_inputs(case, 'vibepass_half')]
        base = execute(case, srcs, seeds, d / tag / 'base')
        base_put = [iorel.value(o) for o in execute(case, [case['source']], seeds, d / 'put_base')['p0']] if seeds else []
        valid, invalid = [], collections.Counter()
        for n in base:
            vals = [iorel.value(o) for o in base[n]]
            pairs = [(a, b) for a, b in zip(base_put, vals) if a is not None]
            if pairs and all(b is not None and same(a, b) for a, b in pairs):
                valid.append(n)
            elif not srcs[int(n[1:])]:
                invalid['empty'] += 1
            elif base[n] and base[n][0][0] == 'exception' and str(base[n][0][1]).startswith('load:'):
                invalid['load_error'] += 1
            elif any(b is not None and b[0] == 'exception' for _, b in pairs):
                invalid['exception'] += 1
            elif any(b is None for _, b in pairs):
                invalid['timeout_or_unparsable'] += 1
            else:
                invalid['mismatch'] += 1
        ks = sorted({q['k'] for q in cq})
        inputs, res, _ = self.truth[cid]
        outs = execute(case, [srcs[int(n[1:])] for n in valid], [inputs[k] for k in ks], d / tag / 'questions') if valid else {}
        puts = [iorel.value(next(q['put'] for q in cq if q['k'] == k)) for k in ks]
        exposing = self.task_facts(cid)['exposing']
        r = dict(valid=len(valid), invalid=dict(invalid), tests=0, true=0, fa=0, unconfirmed=0, consensus_tests=0,
                 consensus_true=0, differs=0, programs_right=0,
                 applies_edit=sum(applies_edit(case, O.concepts(case, cq), s) for s in srcs if s))
        for i in range(len(valid)):
            vals = [iorel.value(o) for o in outs[f'p{i}']]
            r['differs'] += any(v is not None and v[0] == 'ok' and p is not None and p[0] == 'ok' and not same(v, p)
                                for v, p in zip(vals, puts))
            r['programs_right'] += bool(exposing) and all(
                vals[ks.index(k)] is not None and same(vals[ks.index(k)], iorel.value(res['ref'][k])) for k in exposing)
        for j, k in enumerate(ks):
            put = puts[j]
            if put is None or put[0] != 'ok':
                continue  # tc-full: PUT failures give no comparison
            vals = [iorel.value(outs[f'p{i}'][j]) for i in range(len(valid))]
            groups = []
            for v in vals:
                if v is None or v[0] != 'ok' or same(v, put):
                    continue
                g = next((g for g in groups if same(g[0], v)), None)
                if g:
                    g[1] += 1
                else:
                    groups.append([v, 1])
            if groups:
                verdict = self.judge_test(cid, k, max(groups, key=lambda g: g[1])[0])  # max keeps the first of ties
                r['tests'] += 1
                r['true'] += verdict == 'confirmed'
                r['fa'] += verdict != 'confirmed'
                r['unconfirmed'] += verdict == 'unconfirmed'
            if len(vals) >= 3 and all(v is not None and v[0] == 'ok' for v in vals) and all(same(vals[0], v) for v in vals) \
                    and not same(vals[0], put):
                r['consensus_tests'] += 1
                r['consensus_true'] += self.judge_test(cid, k, vals[0]) == 'confirmed'
        r['confirmed'] = r['true'] > 0
        return r

    def arm(self, name, srcs_of):
        per = {cid: self.evaluate(self.cases[cid], srcs_of(cid), name) for cid in TASKS}
        tot = {f: sum(r[f] for r in per.values()) for f in ('valid', 'tests', 'true', 'fa', 'unconfirmed', 'consensus_tests',
                                                             'consensus_true', 'differs', 'programs_right', 'applies_edit')}
        return dict(confirmed_tasks=[c for c in TASKS if per[c]['confirmed']],
                    consensus_tasks=[c for c in TASKS if per[c]['consensus_true']],
                    precision=round(tot['true'] / tot['tests'], 3) if tot['tests'] else None, **tot, per_task=per)


def report(arms):
    for name, a in arms.items():
        print(f"{name:20} confirmed {len(a['confirmed_tasks'])}/6 {a['confirmed_tasks']} consensus {a['consensus_tasks']} "
              f"tests {a['tests']} true {a['true']} FA {a['fa']} valid {a['valid']} differs {a['differs']} "
              f"right {a['programs_right']} edit {a['applies_edit']}")


def score():
    s = Scorer()
    runs = json.loads((OUT / 'runs.json').read_text())
    excluded, strict_excluded = [], []
    arms = {f'sonnet_{arm}': s.arm(f'sonnet_{arm}', lambda cid, arm=arm: sonnet_programs(cid, arm, runs, excluded))
            for arm in ARMS}
    arms.update({f'sonnet_{arm}_strict': s.arm(f'sonnet_{arm}_strict', lambda cid, arm=arm: sonnet_programs(
        cid, arm, runs, strict_excluded, 'strict')) for arm in ARMS})  # sensitivity: amendment-1 rule
    summary = dict(tasks=TASKS, k=K, excluded=sorted(set(excluded)), strict_excluded=sorted(set(strict_excluded)), task_facts={c: s.task_facts(c) for c in TASKS},
                   models=sorted({m for r in runs.values() for m in r['models']}), arms=arms)
    O.immutable(OUT / 'score.json', summary)
    report(arms)
    print('excluded', summary['excluded'], 'facts', summary['task_facts'])


def qwen():
    """Qwen v46 programs on the same tasks (first K and all 10); only after the registered v46 score exists."""
    v46 = json.loads((O.OUT / 'score.json').read_text())
    s = Scorer()
    arms = {f'qwen_{arm}_k{k}': s.arm(f'qwen_{arm}_k{k}', lambda cid, arm=arm, k=k: O.programs(s.cases[cid], arm, None)[:k])
            for k in (K, O.NPROG) for arm in ARMS}
    check = {arm: [c for c in TASKS if (c in arms[f'qwen_{arm}_k{O.NPROG}']['confirmed_tasks'])
                   != (c in v46['arms'][arm]['confirmed'])] for arm in ARMS}
    O.immutable(OUT / 'qwen.json', dict(tasks=TASKS, arms=arms, v46_mismatch=check))
    report(arms)
    print('k10 vs v46 per-task mismatches', check)


if __name__ == '__main__':
    dict(prompts=prompts, audit=audit, score=score, qwen=qwen)[sys.argv[1]]()

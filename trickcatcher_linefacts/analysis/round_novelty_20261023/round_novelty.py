"""Round novelty on saved v11_fair dev outputs (PREREG.md in this folder). CPU only, ref oracle.

Replays oracle executions with analysis/final_protocol.py's own functions, then splits every hybrid sample into
round 1 (the round1_assertions prefix) and round 2 and asks what round 2 adds.

    python -B analysis/round_novelty_20261023/round_novelty.py execute --cache <scratch>/exec.json
    python -B analysis/round_novelty_20261023/round_novelty.py score --cache <scratch>/exec.json
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import random
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
HOME = HERE.parents[1]
sys.path.insert(0, str(HOME / 'analysis'))
import final_protocol as fp   # noqa: E402  (inserts the repo root and imports v11_fair's oracle_b01)

ob = fp.ob
RUN = HOME / 'pipelines/v11_fair/out/humaneval/generation'
ORACLE = HOME / 'pipelines/v11_fair/out/humaneval/oracle'
SAVED = HOME / 'analysis/final_protocol_v11_dev.json'
MODE = 'ref'
HYBRID = ('concept-hybrid', 'placebo-hybrid', 'plain-hybrid')
GATE_ARMS = ('plain', 'concept', 'toolinput', *HYBRID, 'witness-only')


def load():
    run, tasks, rows = fp.load_run(RUN)
    selected = [r for r in rows if r['split'] == 'dev']
    ids = sorted({r['task'] for r in selected})
    witness = {t: list(dict.fromkeys(c for src in tasks[t].get('tool_inputs', [])
                                    if (c := fp.normalize_call(src)))) for t in ids}
    return run, tasks, selected, ids, witness


def execute(cache, workers):
    run, tasks, selected, ids, witness = load()
    data, atols, _ = fp.metadata(run, tasks, 'humaneval')
    with tempfile.TemporaryDirectory(prefix='round_novelty_') as tmp:
        main = fp.execute_records(tasks, selected, ORACLE, data, atols, Path(tmp) / 'arms', workers)
        wit = fp.execute_records(tasks, selected, ORACLE, data, atols, Path(tmp) / 'witness', workers, witness)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(dict(main=main, witness=wit)))
    print(f'cache: {cache} ({len(main)} tasks, {len(wit)} witness tasks)')


def split_calls(row, task):
    """Round-1 calls and round-2 calls (strict round 2 never repeats a round-1 call)."""
    n1 = len(row['round1_assertions'])
    if [a['src'] for a in row['asserts'][:n1]] != row['round1_assertions']:
        raise ValueError(f"round-1 prefix mismatch at {row['task']}/{row['arm']}/{row['sample']}")
    entry = task['entry']
    c1 = list(dict.fromkeys(c for a in row['asserts'][:n1] if (c := ob.call_of(a['src'], entry))))
    c2 = list(dict.fromkeys(c for a in row['asserts'][n1:] if (c := ob.call_of(a['src'], entry))))
    if set(c1) & set(c2):
        raise ValueError(f"round 2 repeats a round-1 call at {row['task']}/{row['arm']}/{row['sample']}")
    return c1, c2


def gate(tasks, selected, ids, witness, ex, judges):
    """Whole-sample numbers must equal the saved v11 dev report before any round split is computed."""
    saved = fp.read_json(SAVED)['oracles'][MODE]['arms']
    rows = {a: [r for r in selected if r['arm'] == a] for a in GATE_ARMS if a != 'witness-only'}
    rows['witness-only'] = [dict(task=t, sample=s, asserts=[dict(src=f'assert {c} == None') for c in witness[t]],
                                 llm_calls=0, n_in=0, n_out=0) for t in ids for s in range(3)]
    bad, witness_samples = [], None
    for arm, rs in rows.items():
        samples = fp.score_samples(tasks, rs, ex['witness' if arm == 'witness-only' else 'main'], judges, MODE)
        m = fp.summarize(samples, 3)
        for key in ('detecting_samples', 'failing', 'correct_failing', 'false_alarms', 'D_I', 'D_I_samples'):
            if m[key] != saved[arm][key]:
                bad.append(f'{arm} {key}: replay {m[key]} vs saved {saved[arm][key]}')
        if arm == 'witness-only':
            witness_samples = samples
    return bad, saved, witness_samples


def score(cache):
    _, tasks, selected, ids, witness = load()
    ex = json.loads(cache.read_text())
    judges = fp.cached_judges(ORACLE)
    bad, saved, witness_samples = gate(tasks, selected, ids, witness, ex, judges)
    if bad:
        (HERE / 'GATE_FAILED.txt').write_text('\n'.join(bad) + '\n')
        sys.exit('GATE FAILED (no outcome computed):\n' + '\n'.join(bad))
    wit_det = {t: witness_samples[t, 0]['detecting'] for t in ids}   # witness-only is the same for every sample

    per = {}   # (arm, task, sample) -> round flags
    for r in selected:
        if r['arm'] not in HYBRID:
            continue
        t, s = r['task'], r['sample']
        c1, c2 = split_calls(r, tasks[t])
        if fp.calls_of(r, tasks[t]) != c1 + c2:
            raise ValueError(f"call split does not cover the sample at {t}/{r['arm']}/{s}")
        recs = ex['main'][str(t)]['calls']
        s1, s2 = ([fp.call_score(recs[c], MODE, judges.get((str(t), c))) for c in cs] for cs in (c1, c2))
        det1, det2 = any(x['detecting'] for x in s1), any(x['detecting'] for x in s2)
        di1, di2 = any(x['d_i'] for x in s1), any(x['d_i'] for x in s2)
        per[r['arm'], t, s] = dict(
            s2=s2, n1=len(c1), n2=len(c2), det1=det1, det2=det2,
            r2_new=det2 and not det1, r2_redundant=det2 and det1,
            r2_new_beyond_tool=det2 and not det1 and not wit_det[t],
            di1=di1, di2=di2, di_new=di2 and not di1,
            fa2=sum(x['failing'] and not x['correct_failing'] for x in s2),
            flag2_first=any(x['flag_correct'] for x in s2) and not any(x['flag_correct'] for x in s1))

    # Amendment 1: budget-matched r2_new, n = min(R2 calls of concept, of placebo) per (task, sample).
    rng = random.Random(f'{fp.SEED}-round-novelty-matched')
    for t in ids:
        for s in range(3):
            c, p = per['concept-hybrid', t, s], per['placebo-hybrid', t, s]
            n = min(c['n2'], p['n2'])
            for v in (c, p):
                v['r2_new_matched'] = 0.0 if v['det1'] else fp.cut(v['s2'], n, rng)

    def total(arm, key):
        return sum(v[key] for (a, _, _), v in per.items() if a == arm)

    arms = {}
    for arm in HYBRID:
        n = sum(a == arm for a, _, _ in per)
        whole = sum(v['det1'] or v['det2'] for (a, _, _), v in per.items() if a == arm)
        if whole != saved[arm]['detecting_samples']:
            sys.exit(f"GATE FAILED: {arm} round split covers {whole} detecting samples, saved {saved[arm]['detecting_samples']}")
        miss1, det2, n2 = n - total(arm, 'det1'), total(arm, 'det2'), total(arm, 'n2')
        arms[arm] = dict(
            samples=n, samples_with_r2=sum(v['n2'] > 0 for (a, _, _), v in per.items() if a == arm),
            r1_calls=total(arm, 'n1'), r2_calls=n2, whole=whole, det1=total(arm, 'det1'), det2=det2,
            r2_new=total(arm, 'r2_new'), r2_redundant=total(arm, 'r2_redundant'),
            redundancy_share=total(arm, 'r2_redundant') / det2 if det2 else None,
            r2_new_beyond_tool=total(arm, 'r2_new_beyond_tool'),
            r2_new_tool_reachable=total(arm, 'r2_new') - total(arm, 'r2_new_beyond_tool'),
            r1_missed=miss1, conditional_novelty=total(arm, 'r2_new') / miss1 if miss1 else None,
            di1=total(arm, 'di1'), di2=total(arm, 'di2'), di_new=total(arm, 'di_new'),
            fa2=total(arm, 'fa2'), fa2_per_r2_call=total(arm, 'fa2') / n2 if n2 else None,
            flag2_first=total(arm, 'flag2_first'),
            tasks_r2_new=sorted({t for (a, t, _), v in per.items() if a == arm and v['r2_new']}))
        if arm != 'plain-hybrid':
            arms[arm]['r2_new_matched'] = total(arm, 'r2_new_matched')

    def compare(a, b, key, lower_better=False, note=None):
        x, y = defaultdict(float), defaultdict(float)
        for (arm, t, _), v in per.items():
            if arm == a:
                x[t] += v[key]
            elif arm == b:
                y[t] += v[key]
        sign = -1 if lower_better else 1
        wins = sum(sign * (x[t] - y[t]) > 1e-9 for t in ids)
        losses = sum(sign * (x[t] - y[t]) < -1e-9 for t in ids)
        return dict(first=a, second=b, metric=key, lower_better=lower_better, note=note,
                    first_total=sum(x.values()), second_total=sum(y.values()), wins=wins, losses=losses,
                    ties=len(ids) - wins - losses, p_two_sided=fp.sign_test(wins, losses))

    primary_raw = compare('concept-hybrid', 'placebo-hybrid', 'r2_new', note='registered primary, descriptive after amendment 1')
    co_primary = compare('concept-hybrid', 'placebo-hybrid', 'r2_new_matched', note='amendment 1 decision test')
    secondary = [compare('concept-hybrid', 'plain-hybrid', 'r2_new'),
                 compare('concept-hybrid', 'placebo-hybrid', 'det2'),
                 compare('concept-hybrid', 'placebo-hybrid', 'r2_new_beyond_tool'),
                 compare('concept-hybrid', 'placebo-hybrid', 'fa2', lower_better=True,
                         note='raw count, not interpreted (unequal R2 calls)'),
                 compare('placebo-hybrid', 'plain-hybrid', 'r2_new', note='exploratory')]
    sets = {a: set(arms[a]['tasks_r2_new']) for a in HYBRID}
    overlap = dict(concept_only_vs_placebo=sorted(sets['concept-hybrid'] - sets['placebo-hybrid']),
                   placebo_only_vs_concept=sorted(sets['placebo-hybrid'] - sets['concept-hybrid']),
                   concept_and_placebo=sorted(sets['concept-hybrid'] & sets['placebo-hybrid']),
                   in_all_three=sorted(set.intersection(*sets.values())))
    c, p = arms['concept-hybrid'], arms['placebo-hybrid']
    signal = (co_primary['wins'] > co_primary['losses'] and co_primary['p_two_sided'] < 0.05
              and c['r2_new_beyond_tool'] >= p['r2_new_beyond_tool'])
    result = dict(gate='PASS', mode=MODE, tasks=len(ids), K=3, witness_detecting_tasks=sum(wit_det.values()),
                  arms=arms, primary_raw=primary_raw, co_primary_matched=co_primary, secondary=secondary,
                  task_overlap=overlap, decision='SIGNAL' if signal else 'NO SIGNAL')
    (HERE / 'results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ('decision', 'primary_raw', 'co_primary_matched')}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('step', choices=('execute', 'score'))
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    execute(args.cache, args.workers) if args.step == 'execute' else score(args.cache)


if __name__ == '__main__':
    main()

"""CPU checks; PF/HumanEval+ material is evaluation-only, never passed to ranking."""
from __future__ import annotations
import ast
import json
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = 'trickcatcher_linefacts.pipelines.' + Path(__file__).resolve().parent.name
from . import paths


def label_worker(task, out_path):
    import contextlib, io
    from . import offline, spec_facts as S
    from .tracer import call, dcopy, load_module
    n, entry, src = task['task'], task['entry'], task['put']
    if task['split'] != 'dev':
        raise ValueError('pilot/design labels are forbidden')
    hep = next(r for r in map(json.loads, paths.dataset_paths()['hep'].read_text().splitlines())
               if r['task_id'] == f'HumanEval/{n}')
    pg = load_module(src)
    put = pg[entry]
    cur, REC, FAIL = [None], {}, {}

    def cand(*a, **k):
        REC[cur[0]] = (dcopy(a), dcopy(k))
        stt, val = call(put, (a, k))
        if stt != "ok":
            raise RuntimeError(stt)
        return val

    g = dict(pg)
    g.update({"__cur": cur, "__fail": lambda i, e: FAIL.__setitem__(i, type(e).__name__), "__name__": "__plus__"})
    with contextlib.redirect_stdout(io.StringIO()):
        exec(offline.plus_check_src(hep["test"]), g)
        g["check"](cand)
    spec = json.loads((paths.DATA_OUT / "specfacts" / f"{n}.json").read_text())
    res = []
    for f in spec["facts"]:
        c = f["input_class"]
        h = [i for i, (a, k) in REC.items() if not k and c["param"] < len(a) and S.in_class(c["cls"], a[c["param"]])]
        res.append(dict(fail_hits=sum(i in FAIL for i in h), pass_hits=sum(i not in FAIL for i in h)))
    json.dump(dict(task=n, n_plus=len(REC), n_fail=len(FAIL), spec=res), open(out_path, "w"))



def labels(layout, tasks, workers):
    from .v4_runtime import immutable
    directory = layout.root / 'checks' / 'labels'
    directory.mkdir(parents=True, exist_ok=True)
    def one(t):
        n = t['task']
        jp, op = directory / f'{n}.job.json', directory / f'{n}.json'
        immutable(jp, {k: t[k] for k in ('task', 'entry', 'put', 'split')})
        if op.exists(): return
        r = subprocess.run(['timeout', '-k', '5', '3600', 'unshare', '-rn', sys.executable, '-I', '-B',
                            str(Path(__file__).resolve()), 'label-worker', str(jp), str(op)],
                           env=paths.worker_env(), capture_output=True, text=True)
        if r.returncode or not op.exists():
            raise RuntimeError(f'PF worker {n} failed rc={r.returncode}: {r.stderr[-1000:]}')
    with ThreadPoolExecutor(workers) as pool: list(pool.map(one, tasks))


def pf(h):
    total = h['fail_hits'] + h['pass_hits']
    return h['fail_hits'] / total if total else None


def check_selection(layout, historical, tasks):
    from . import facts, hint_rank
    saved = json.loads((historical / 'hint_rank/results.json').read_text())['rules']['LR[noref+mutref]']
    old = {t['task']: t for t in json.loads((historical / 'tasks_v7_all.json').read_text())['tasks']}
    counts, good = dict(even=0, odd=0), dict(even=0, odd=0)
    selection_errors, feature_errors, refs_errors, witness_errors, derivation_errors = [], [], [], [], []
    feature_drift, unexpected_feature_errors = [], []
    changed, unchanged, same_set = [], [], []
    selections = {}
    for t in tasks:
        n = t['task']
        feat = json.loads((layout.root / 'rank' / f'{n}.json').read_text())
        rows = feat['rows']
        reference = json.loads((historical / 'hint_rank/feat' / f'{n}.json').read_text())
        if [(r['src'], r['idx'], hint_rank.x_of(r)) for r in rows] != [(r['src'], r['idx'], hint_rank.x_of(r)) for r in reference['rows']]:
            feature_errors.append(n)
            safe_drift = len(rows) == len(reference['rows'])
            for old_row, new_row in zip(reference['rows'], rows):
                if hint_rank.x_of(old_row) == hint_rank.x_of(new_row): continue
                differences = {key: [old_row[key], new_row[key]] for key in old_row.keys() & new_row.keys()
                               if old_row[key] != new_row[key]}
                feature_drift.append(dict(task=n, src=new_row['src'], idx=new_row['idx'], differences=differences))
                safe_drift &= new_row['slot'] == 'LOOP' and set(differences) <= {'hit_frac', 'n_hit', 'n_eval', 'crash'}
            safe_drift &= hint_rank.select(n, rows) == hint_rank.select(n, reference['rows'])
            if not safe_drift: unexpected_feature_errors.append(n)
        if feat['witness_mismatch']: witness_errors.append(n)
        exec_rec = json.loads((layout.refs / 'exec' / f'{n}.json').read_text())
        if feat['n_refs'] != exec_rec['n_survivors']['ref']: refs_errors.append(n)
        selected = hint_rank.select(n, rows)
        # Includes the no-failure dev task absent from results.json's measured cohort.
        if selected != hint_rank.select(n, reference['rows']): selection_errors.append(n)
        code = json.loads((layout.facts / f'{n}.json').read_text())
        spec = json.loads((layout.specfacts / f'{n}.json').read_text())
        pool = [(code if r['src'] == 'code' else spec)['facts'][r['idx']] for r in rows]
        top = facts.pick(pool, n, rank_rows=rows)
        if t['concept_facts'] != [f['text'] for f in top] or [f['text'] for f in t['concept_meta']] != t['concept_facts']:
            selection_errors.append(n)
        if t['tool_inputs'] != list(dict.fromkeys(f['witness_call'] for f in top if f['witness_call'])):
            derivation_errors.append(n)
        if t['placebo_facts'] != [f['text'] for f in t['placebo_meta']]: derivation_errors.append(n)
        if t['concept_facts'] == old[n]['concept_facts']:
            unchanged.append(n)
            for key in ('placebo_facts', 'tool_inputs'):
                if t[key] != old[n][key]: derivation_errors.append([n, key])
        else:
            changed.append(n)
        if set(t['concept_facts']) == set(old[n]['concept_facts']): same_set.append(n)
        selections[str(n)] = [dict(src=rows[j]['src'], idx=rows[j]['idx']) for j in selected]
        code_labels = json.loads((historical / 'offline_v6_report' / f'{n}.json').read_text())
        spec_labels = json.loads((layout.root / 'checks/labels' / f'{n}.json').read_text())
        if code_labels['n_fail'] == 0: continue  # analysis excludes PUTs without a failing plus test
        if selected != saved['sel'].get(str(n)): selection_errors.append(n)
        part = 'odd' if n % 2 else 'even'
        counts[part] += 1
        pfs = [pf((code_labels['concept'] if rows[j]['src'] == 'code' else spec_labels['spec'])[rows[j]['idx']]) for j in selected]
        good[part] += any(p is not None and p >= .5 for p in pfs)
    return dict(dev_tasks=len(tasks), measured_tasks=counts, good_at_3=good,
                changed_hints=len(changed), unchanged_hints=len(unchanged), same_unordered_hint_set=len(same_set),
                changed_task_ids=changed, unchanged_task_ids=unchanged,
                analysis_selection_mismatches=selection_errors, feature_mismatches=feature_errors,
                feature_drift=feature_drift, unexpected_feature_mismatches=unexpected_feature_errors,
                ref_survivor_mismatches=refs_errors, witness_mismatches=witness_errors,
                bundle_derivation_mismatches=derivation_errors, selections=selections)


def check_requests(layout, historical, tasks, ids):
    from . import gen_inputs, gen_prompts, prompts, run_v4, v4_prompts, v4_runtime
    from .offline_client import OfflineClient, request
    record = historical / 'gen2_qwen7b_v7hyb_v4_r2'
    rows = {(r['task'], r['arm'], r['sample']): r
            for r in map(json.loads, (record / 'gen.jsonl').read_text().splitlines())}
    client = OfflineClient(record / 'cache')
    checked, wrong, witness_diff = 0, [], []
    fresh_wrong, replayed_failures = [], []
    python = v4_runtime.interpreter()
    for t in tasks:
        if t['task'] not in ids: continue
        candidates = [dict(input_repr=repr(tuple(ast.literal_eval(x['input_repr']))))
                      for x in gen_inputs.witness_candidates(t)]
        flagged = run_v4.classify(t, layout.root / 'checks/first_requests' / str(t['task']), python, candidates=candidates)
        selected = [r for r in flagged['records'] if r['valid']][:3]
        for sample in range(paths.CONFIG['K']):
            saved = rows[t['task'], 'toolinput', sample]
            oracle_selected = selected
            if selected != saved['selected_inputs']:
                witness_diff.append([t['task'], sample])
                error = saved['stage1_summaries'][0].get('classification_error')
                if error:
                    # Same recorded-state replay used by v7/test_equivalence.py.
                    with patch.object(run_v4.v4_runtime, 'isolated', side_effect=RuntimeError(error)):
                        fallback = run_v4.classify(t, layout.root / 'checks/recorded_failure', python, candidates=candidates)
                    if fallback['summary'] != saved['stage1_summaries'][0]:
                        raise AssertionError('classifier fallback differs from v7')
                    oracle_selected = [r for r in fallback['records'] if r['valid']][:3]
                    replayed_failures.append(dict(task=t['task'], sample=sample, error=error))
            for arm in v4_prompts.ARMS:
                alias = 'plain' if arm == 'plain-hybrid' else 'concept' if arm == 'concept-hybrid' else arm
                if alias in ('plain', 'concept', 'placebo-hybrid'):
                    messages = gen_prompts.messages(*prompts.build('placebo' if alias == 'placebo-hybrid' else alias, t)); stage = 0
                elif alias == 'gen-plain':
                    messages = gen_prompts.generator_messages(alias, t); stage = 1
                else:
                    messages = gen_prompts.oracle_messages(t, oracle_selected); stage = 2
                seed = v4_prompts.seed(t['task'], alias, sample, stage)
                fresh_messages = gen_prompts.oracle_messages(t, selected) if alias == 'toolinput' else messages
                if request(fresh_messages, seed)[0] != rows[t['task'], arm, sample]['calls'][0]['key']:
                    fresh_wrong.append([t['task'], arm, sample])
                key = request(messages, seed)[0]
                if key != rows[t['task'], arm, sample]['calls'][0]['key']:
                    wrong.append([t['task'], arm, sample])
                # Verify the actual immutable response cache exists for this request too.
                client.chat(messages, seed)
                checked += 1
    return dict(tasks=len(ids), arms=len(v4_prompts.ARMS), samples=paths.CONFIG['K'],
                requests=checked, cache_hits=len(client.hits), cache_misses=len(client.misses),
                key_mismatches=wrong, witness_selection_mismatches=witness_diff,
                fresh_key_mismatches=fresh_wrong, fresh_equal=checked-len(fresh_wrong),
                recorded_state_equal=checked-len(wrong), replayed_recorded_worker_failures=replayed_failures,
                all_equal=not wrong and len(witness_diff) == len(replayed_failures) and not client.misses)


def main(workers=12):
    from .run import Layout
    layout = Layout()
    historical = paths.REPO / 'trickcatcher_linefacts/out'
    if not layout.hybrid.is_file(): raise ValueError('run refs and bundle before checks')
    standard = json.loads(layout.all.read_text())['tasks']
    hybrid = json.loads(layout.hybrid.read_text())['tasks']
    dev = [t for t in standard if t['split'] == 'dev']
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden')), \
         patch.object(socket, 'create_connection', side_effect=AssertionError('network forbidden')):
        labels(layout, dev, workers)
        selection = check_selection(layout, historical, dev)
        requests = check_requests(layout, historical, hybrid, selection['unchanged_task_ids'])
    summary = dict(selection=selection, round1=requests)
    dest = layout.root / 'checks/report.json'
    dest.write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k: {n: v for n, v in val.items() if n not in ('selections', 'changed_task_ids', 'unchanged_task_ids')}
                      for k, val in summary.items()}, indent=2))
    print('CPU report:', dest)
    errors = [selection[k] for k in ('analysis_selection_mismatches', 'unexpected_feature_mismatches',
              'ref_survivor_mismatches', 'witness_mismatches', 'bundle_derivation_mismatches')]
    if any(errors) or selection['good_at_3'] != dict(even=37, odd=35) or not requests['all_equal']:
        raise SystemExit(1)


if __name__ == '__main__':
    if sys.argv[1:2] == ['label-worker']:
        label_worker(json.loads(Path(sys.argv[2]).read_text()), sys.argv[3])
    else:
        import argparse
        ap = argparse.ArgumentParser(description=__doc__)
        ap.add_argument('--workers', type=int, default=12)
        main(ap.parse_args().workers)

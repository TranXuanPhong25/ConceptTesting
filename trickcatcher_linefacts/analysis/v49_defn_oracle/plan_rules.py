"""Post-score branch rules of PLAN_NEXT_v50.md (written 2026-10-23 before any v48/v49 output; revision 1 after an
independent Opus review, still before any output). Usage (repo root):
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v49_defn_oracle/plan_rules.py
Needs v48 and v49 score.json. Classifies every `defn`-eligible task with v48's `decomposition` (adapter: vote = v49
`primary`, label = v49 `primary` label) on the whole decisive universe (official reach where score computed it, else
valid ∧ ref ≠ PUT), checks the recomputation against score.json, then applies the fixed precedence
R1 > R1b > R6 > R3 > class plurality (R2/R3v/R4/R7) > R5. Writes out/.../v49_defn_oracle/plan_v50_rules.json.
"""
import collections
import json
import sys

sys.dont_write_bytecode = True
from trickcatcher_linefacts.analysis.v49_defn_oracle import oracle as O

E = O.E
CLASS_RULE = {'b2_variants_failed': 'R2', 'c_vote_wrong_variant_had_ref': 'R3v', 'd_vote_wrong_value': 'R3v',
              'b_common_mode': 'R4', 'a_no_exposing_input': 'R7'}
CLASS_ORDER = ('R2', 'R3v', 'R4', 'R7')  # tie-break of the plurality
BRANCH = dict(R1='v50-H after the manual audit (audited defn-only wins must keep margin >= 3 on >= 3 problems)',
              R1b='v50-FA: FA control on the same inputs (defn∧tc cross, validator), not close',
              R6='v50-F: $0 CPU re-score of v48 arms with the defn/brute primary oracle (mechanism check), then ask user',
              R3='stop Qwen program oracle; stronger model only after asking user',
              R3v='stop Qwen program oracle (majority value wrong); stronger model only after asking user',
              R2='v50-S small-scope exhaustion judged by defn (keep brute arm)',
              R4='report + Opus critique (common-mode at spec level)',
              R7='no new input selection (PLAN_NEXT_v49 C); small-scope exhaustion only on a fresh cohort',
              R5='v50-V validator concept (B5/F1b miner baseline)')


def exposing(t, put):
    """Official reach where score computed it (menu ∪ llm_code); elsewhere valid ∧ ref ≠ PUT."""
    if t['exposing'] is not None:
        return bool(t['exposing'])
    return bool(t['valid'] and t['ref'] is not None and put is not None and not E.same(put, t['ref']))


def task_view(rec, truth, labels):
    """v48 decomposition of the `defn` family on all decisive inputs."""
    fam = rec['families']['defn']
    rows, view = {}, {}
    for lit, row in rec['inputs'].items():
        progs = row['programs']['defn']
        v = O.votes(row['put'], list(progs.values()))
        rows[lit] = dict(put=row['put'], programs=dict(progs), vote=v['primary'])
        t = truth[lit]
        view[lit] = dict(t, exposing=exposing(t, E.iorel.value(row['put'])), vote=labels[lit]['primary'])
    d = E.decomposition(set(rows), rows, view, fam['valid_programs'])
    tests = len(E.emitted(set(rows), rows, 'vote', 20))
    return d, tests


def rules(v49, tasks):
    """Pure rule evaluation. `tasks`: case_id -> dict(problem_id, valid, resource_only, primary, fa_split, tests)."""
    dec = v49['summary']['decision']
    prim, sec, vs_tc = dec['primary'], dec['secondary'], dec['defn_vs_tc']
    value, why = {}, {}
    value['R1'] = prim['verdict'] == 'GO'
    value['R1b'] = prim['checks']['confirmed_task_margin'] and prim['checks']['extra_problem_span'] and not prim['checks']['fa_no_worse']
    value['R6'] = sec['verdict'] == 'GO' or vs_tc['verdict'] == 'GO'
    capable = {t['problem_id'] for t in tasks.values() if t['valid'] + t['resource_only'] >= 2}
    split = sum((collections.Counter(t['fa_split']) for t in tasks.values() if t['valid'] >= 2), collections.Counter())
    resolved = split['put_right'] + split['put_wrong_wrong_value'] + split['unconfirmed_official']
    confirmed = sum(t['tests'] - sum(t['fa_split'].values()) for t in tasks.values() if t['valid'] >= 2)
    wrong = split['put_right'] + split['put_wrong_wrong_value']
    wrong_share = wrong / (resolved + confirmed) if resolved + confirmed else None
    value['R3'] = len(capable) < 12 or (wrong_share is not None and wrong_share >= 0.5)
    why['R3'] = dict(capable_problems=len(capable), wrong_value_share_valid_resolved=wrong_share)
    misses = collections.defaultdict(list)
    for cid, t in tasks.items():
        if t['valid'] >= 2 and t['primary'] in CLASS_RULE:
            misses[CLASS_RULE[t['primary']]].append(cid)
    qualified = [r for r in CLASS_ORDER if len(misses[r]) >= 3 and len({tasks[c]['problem_id'] for c in misses[r]}) >= 3]
    plural = max(qualified, key=lambda r: (len(misses[r]), -CLASS_ORDER.index(r)), default=None)
    fa = sum(split.values())
    value['R5'] = fa >= 10 and split['invalid_input'] * 2 >= fa
    why['R5'] = dict(defn_fa_tests=fa, invalid_input=split['invalid_input'])
    order = [('R1', value['R1']), ('R1b', value['R1b']), ('R6', value['R6']), ('R3', value['R3']),
             (plural, plural is not None), ('R5', value['R5'])]
    fired = next((r for r, v in order if v), None)
    status = 'pending_manual_audit' if fired == 'R1' and v49['summary'].get('concept_attribution') == 'pending_manual_audit' else 'final'
    return dict(fired=fired, status=status, branch=BRANCH.get(fired, 'close definitional-oracle direction + critique'),
                rules=value, why=why, miss_classes={r: sorted(c, key=int) for r, c in misses.items()},
                plurality=plural, defn_fa_split_eligible=dict(split),
                class_counts=dict(collections.Counter(t['primary'] for t in tasks.values() if t['valid'] >= 2)))


def main():
    v49 = json.loads((O.OUT / 'score.json').read_text())
    v48 = json.loads((E.OUT / 'score.json').read_text())
    inv = O.Inventory()
    _, ready = O.score_inputs(inv)
    if ready is None:
        raise SystemExit('v49 records incomplete')
    cohort, _, records, picks = ready
    run = E.ft_run.FTRun('vibepass_half')
    official = E.Reference(run)
    official.root = O.OUT / 'references' / 'official'
    cases = {c['case_id']: c for c in run.cases}
    prep = inv.read(E.select.OUT / 'prepared.json')
    scored = {r['case_id']: r for r in v49['rows']}
    tasks = {}
    for cid in cohort:
        rec = records[cid]
        truth = O.task_truth(inv, cases[cid], rec, official, E.all_inputs(prep[cid]) | set(picks[cid]))
        rows = O.oracle_rows(rec, 'defn')
        labels = O.labels_for(rows, truth)
        d, tests = task_view(rec, truth, labels)
        m = scored[cid]['input_sets']['decisive']['defn']['primary']['capped']
        split = d['fa_split']['capped']
        if tests != m['tests'] or sum(split.values()) != m['fa_tests']:  # recomputation must equal score's view
            raise SystemExit(f'task {cid}: recomputed {tests} tests/{sum(split.values())} FA != score {m["tests"]}/{m["fa_tests"]}')
        diag = scored[cid]['diagnostics']['defn']
        tasks[cid] = dict(problem_id=rec['problem_id'], valid=diag['valid_programs'],
                          resource_only=diag['rejected_resource_only'], primary=d['primary'], fa_split=split, tests=tests,
                          exposing_inputs=d['exposing_inputs'], exposing_classes=d['exposing_classes'])
    result = rules(v49, tasks)
    v48_split = sum((collections.Counter(r['failures']['llm_code']['fa_split']['capped']) for r in v48['rows']),
                    collections.Counter())
    result.update(tasks=tasks, v48_llm_code_tc_fa_split_report_only=dict(v48_split),
                  v49_score_sha256=O.digest(v49), v48_score_sha256=O.digest(v48))
    O.immutable(O.OUT / 'plan_v50_rules.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'tasks'}, indent=2))


if __name__ == '__main__':
    main()

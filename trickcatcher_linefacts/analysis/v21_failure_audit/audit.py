"""Retrospective read-only audit of frozen v21 artifacts. No model/PUT/reference execution.

Run with the dedicated V4 interpreter: python -m
trickcatcher_linefacts.analysis.v21_failure_audit.audit
"""
import ast
import collections
import hashlib
import importlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PIPELINE = REPO / 'trickcatcher_linefacts/pipelines/v21_flowtools'
RUNS = REPO / 'trickcatcher_linefacts/out/pipelines/v21_flowtools/humaneval/flowrun'
HERE = Path(__file__).resolve().parent
READS = {}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def read(path):
    raw = path.read_bytes()
    READS[str(path.relative_to(REPO))] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def verified(root):
    protocol = read(root / 'protocol.json')
    frozen = read(root / 'generation_frozen.json')
    for name, expected in frozen.items():
        path = (root / name).resolve()
        if root.resolve() not in path.parents:
            raise ValueError('manifest_path_escape')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('generation_hash_mismatch:' + name)
    for name, expected in protocol['sources'].items():
        if hashlib.sha256((PIPELINE / name).read_bytes()).hexdigest() != expected:
            raise ValueError('source_hash_mismatch:' + name)
    return protocol, frozen


def tool_counts(events):
    counts, signatures = collections.Counter(), []
    rounds = collections.defaultdict(list)
    for event in events:
        if event['type'] != 'action':
            continue
        action, result = event['request']['action'], event['result']
        if not isinstance(action, dict):
            counts['non_object_action'] += 1
            continue
        tool = action.get('tool', 'missing_tool')
        counts['actions'] += 1
        counts['tool:' + tool] += 1
        counts['linked_to_hypothesis'] += bool(action.get('hypothesis'))
        counts['snapshot_names_requested'] += tool == 'replay_input' and bool(action.get('names'))
        counts['action_error'] += result.get('status') != 'ok'
        if result.get('status') != 'ok':
            counts['error:' + result.get('error', 'unspecified')] += 1
        sig = digest(action)
        signatures.append(sig)
        rounds[event['request']['round']].append(sig)
    counts['repeated_actions_beyond_first'] = len(signatures) - len(set(signatures))
    counts['same_nonempty_query_list_in_both_rounds'] = bool(rounds[1]) and rounds[1] == rounds[2]
    return dict(counts)


def core(root):
    protocol, frozen = verified(root)
    score = read(root / 'score.json')
    per_case, per_arm = [], collections.defaultdict(collections.Counter)
    for cid in protocol['cases']:
        case = root / 'cases' / cid
        shared = read(case / 'shared.json')
        hyps = shared['hypotheses']
        row = dict(case=cid, mismatch_hypotheses=len(hyps),
                   hypotheses_with_unmapped_lines=sum(bool(h['unmapped_lines']) for h in hyps),
                   unmapped_lines=[h['unmapped_lines'] for h in hyps if h['unmapped_lines']],
                   hypotheses_without_source_ids=sum(not h['source_ids'] for h in hyps),
                   hypotheses_source_ids=[h['source_ids'] for h in hyps],
                   hypothesis_conditions=[h['condition'] for h in hyps],
                   common_inputs=len(shared['common']),
                   common_native_checked=sum(bool(w.get('native_checked')) for w in shared['common']),
                   common_trace_proven=sum(bool(w.get('all_invocations_proven')) for w in shared['common']),
                   cfg_supported=shared['cfg_supported'],
                   concept_has_quote=bool((shared['concept'] or {}).get('quote')))
        ids = list(dict.fromkeys(i for h in hyps for i in h['source_ids']))
        row['source_ids_beyond_replay_request_cap'] = max(0, len(ids) - protocol['flowtools']['max_names'])
        for arm in protocol['arms']:
            result = read(case / 'arms' / arm / 'result.json')
            path = case / 'arms' / arm / 'tools/ledger.json'
            counts = tool_counts(read(path)['events']) if path.exists() else {}
            per_arm[arm].update(counts)
            row.setdefault('tools', {})[arm] = counts
            if arm == 'agent-tools':
                row['agent_errors'] = result['errors']
            # This is what the runner recorded, not an inference about model-internal reasoning.
            row.setdefault('final_input_counts', {})[arm] = len(result.get('final_executions') or [])
        per_case.append(row)
    overall = dict(tasks=len(per_case), hypotheses=sum(r['mismatch_hypotheses'] for r in per_case),
                   cases_without_hypothesis=sum(not r['mismatch_hypotheses'] for r in per_case),
                   hypotheses_with_unmapped_lines=sum(r['hypotheses_with_unmapped_lines'] for r in per_case),
                   hypotheses_without_source_ids=sum(r['hypotheses_without_source_ids'] for r in per_case),
                   concepts_with_quote=sum(r['concept_has_quote'] for r in per_case),
                   cases_with_replay_observation_cap_loss=sum(r['source_ids_beyond_replay_request_cap'] > 0 for r in per_case),
                   common_inputs=sum(r['common_inputs'] for r in per_case),
                   common_native_checked=sum(r['common_native_checked'] for r in per_case),
                   common_trace_proven=sum(r['common_trace_proven'] for r in per_case))
    arms = {}
    for arm, saved in score['arms'].items():
        arms[arm] = dict(tools=dict(per_arm[arm]), **{k: saved.get(k, 0) for k in (
            'tasks_confirmed', 'tasks_input_discrepancy', 'confirmed_tests', 'false_alarms',
            'tasks_with_false_alarm', 'discrepancy_wrong_expected', 'admissible', 'invalid_inputs', 'schema_errors')})
    return dict(frozen_files_verified=len(frozen), current_source_hashes_verified=len(protocol['sources']),
                overall=overall, arms=arms, cases=per_case)


def source_for(case):
    """Existing worker jobs only. This reads source; never compiles or executes it."""
    path = next(iter(sorted(case.glob('arms/*/executions/*/job.json'))), None)
    if path is None:
        path = next(iter(sorted(case.glob('executions/*/job.json'))), None)
    if path is None:
        raise ValueError('worker_source_missing:' + case.name)
    job = read(path)
    shared = read(case / 'shared.json')
    sha = hashlib.sha256(job['source'].encode()).hexdigest()
    source_prefixes = {uid.split(':')[0] for h in shared['hypotheses'] for uid in h['source_ids']}
    if source_prefixes and source_prefixes != {sha}:
        raise ValueError('worker_source_does_not_match_frozen_hypothesis')
    return job, str(path.relative_to(case.parents[1]))


def cached_labels(root, score, parse_module, tools_module):
    """Read saved reference jobs/results; no fallback to Reference or native execution."""
    by_ref, ref_sources = {}, collections.defaultdict(set)
    for path in sorted((root / 'reference').glob('*/job.json')):
        job, result = read(path), read(path.with_name('result.json'))
        key = (job['entry'], job['input_repr'])
        ref_sources[job['entry']].add(hashlib.sha256(job['source'].encode()).hexdigest())
        if key in by_ref and by_ref[key] != result:
            raise ValueError('ambiguous_cached_reference')
        by_ref[key] = result
    if any(len(hashes) != 1 for hashes in ref_sources.values()):
        raise ValueError('multiple_reference_sources_for_entry')
    out, aggregate = [], collections.defaultdict(collections.Counter)
    for cid in read(root / 'protocol.json')['cases']:
        case = root / 'cases' / cid
        job, source_path = source_for(case)
        fn = next(n for n in ast.parse(job['source']).body if isinstance(n, ast.FunctionDef) and n.name == job['entry'])
        arity = dict(positional=len(fn.args.posonlyargs + fn.args.args), required=len(fn.args.posonlyargs + fn.args.args) - len(fn.args.defaults),
                     varargs=fn.args.vararg is not None, required_keyword_only=any(x is None for x in fn.args.kw_defaults))
        for arm in read(root / 'protocol.json')['arms']:
            rec = read(case / 'arms' / arm / 'result.json')
            expected = {}
            for test in (rec.get('final') or {}).get('tests', []):
                try:
                    lit = repr(tools_module.parse_call(test['arguments'], arity))
                except (ValueError, TypeError):
                    continue
                expected.setdefault(lit, test['expected'])
            for ex in rec.get('final_executions') or []:
                if ex.get('status') != 'ok' or ex.get('domain_filter') != 'accepted':
                    continue
                put = parse_module.put_observation(ex)
                saved = by_ref.get((job['entry'], ex['input']))
                truth = None
                if saved is not None and saved.get('status') == 'exception':
                    truth = ('exception', saved['exception_type'])
                elif saved is not None and saved.get('status') == 'ok' and saved.get('output_repr') is not None:
                    truth = parse_module.parse_expected(saved['output_repr'])
                if put is None or truth is None:
                    aggregate[arm]['unscored'] += 1
                    continue
                disc = not parse_module.same(put, truth)
                aggregate[arm]['input_discrepancy'] += disc
                label = 'witness_discrepancy' if disc else 'witness_pass'
                exp_text = expected.get(ex['input'], '')
                if arm != 'witness-only':
                    exp = parse_module.parse_expected(exp_text)
                    if exp is None:
                        label = 'unparseable_expected'
                    elif disc:
                        label = 'confirmed_detection' if parse_module.same(exp, truth) else 'discrepancy_wrong_expected'
                    else:
                        label = 'passing_test' if parse_module.same(exp, put) else 'false_alarm'
                aggregate[arm][label] += 1
                out.append(dict(case=cid, arm=arm, input=ex['input'], expected=exp_text, label=label,
                                put=ex.get('output'), reference=saved.get('output_repr'),
                                put_exception=ex.get('exception_type'), reference_exception=saved.get('exception_type'),
                                trace=ex.get('trace_summary'), source_job=source_path))
    for arm, counts in aggregate.items():
        for label, key in [('confirmed_detection', 'confirmed_tests'), ('false_alarm', 'false_alarms'),
                           ('discrepancy_wrong_expected', 'discrepancy_wrong_expected')]:
            if counts[label] != score['arms'][arm].get(key, 0):
                raise ValueError('score_reconciliation_failed:' + arm + ':' + label)
    selected = {('90', '([1, 1],)'), ('131', '(2468,)'), ('116', '([-2, -3, -4, -5, -6],)')}
    return dict(reference_cache_entries=len(by_ref), per_arm={k: dict(v) for k, v in aggregate.items()},
                illustrative_inputs=[r for r in out if (r['case'], r['input']) in selected],
                classified_inputs=len(out),
                scores_reconciled=True)


def main():
    report = dict(scope='post-hoc descriptive audit; no new generation/execution; no semantic accuracy claim',
                  cohorts={name: core(RUNS / name) for name in ('diag16', 'pilot20')})
    # Imports only after the exact parser/helper source hashes have been verified above.
    mod = importlib.import_module('trickcatcher_linefacts.pipelines.v21_flowtools.flow_run')
    tools = importlib.import_module('trickcatcher_linefacts.pipelines.v21_flowtools.flow_tools')
    report['pilot20_cached_input_labels'] = cached_labels(RUNS / 'pilot20', read(RUNS / 'pilot20/score.json'), mod, tools)
    snapshots = {}
    for cid in ('0', '82', '90', '108', '116', '131', '143', '151'):
        job, source_path = source_for(RUNS / 'pilot20/cases' / cid)
        snapshots[cid] = dict(source=job['source'], source_job=source_path,
                              source_sha256=hashlib.sha256(job['source'].encode()).hexdigest())
    report['illustrative_source_snapshots'] = snapshots
    report['provenance'] = dict(read_files=len(READS), readset_sha256=digest(READS), model_calls=0,
                                PUT_executions=0, reference_executions=0)
    dest = HERE / 'audit.json'
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if dest.exists() and dest.read_text() != text:
        raise ValueError('audit_output_drift_use_new_version')
    if not dest.exists():
        dest.write_text(text)
    for name, rec in report['cohorts'].items():
        print(name, json.dumps(rec['overall']), 'agent', json.dumps(rec['arms']['agent-tools']['tools']))
    print('Saved labels reconcile with frozen score; audit', report['provenance'])


if __name__ == '__main__':
    main()

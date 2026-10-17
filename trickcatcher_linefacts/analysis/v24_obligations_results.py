"""Read-only completion audit. Never repairs, swaps fields, strips fences or executes new inputs."""
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.pipelines.v24_obligations import experiment as e
from trickcatcher_linefacts.pipelines.v24_obligations import fixtures
from trickcatcher_linefacts.pipelines.v24_obligations.binding import observation
from trickcatcher_linefacts.pipelines.v24_obligations.common import digest, immutable, strict_json

REVIEW = {
    'f01': 'Sorting sketch in wrong field; loose element typing, unsupported lambda/attribute, no exception guard. Core behavior correct.',
    'f02': 'Behavior recognizes returned dedup but initial hypothesis falsely says it preserves multiplicity; raw revision uses out-of-domain non-list fault.',
    'f03': 'Wrong-field sketch only checks nonnegative integer; does not check count or arguments and permits bool. Core behavior correct.',
    'f04': 'Strict comparison recognized, but trigger is passing public base [1,3],2 and count reasoning is incorrect.',
    'f05': 'Wrong-field sketch ignores observation, computing membership condition instead of checking returned value. Initial consistent supported by source.',
    'f06': 'Behavior mistakes set equality for subset; raw initial consistent misses bug. Only valid final hypothesis uses equality trigger where spec/PUT agree and out-of-domain noniterability rationale.',
    'f13': 'Undefined suitability not acknowledged; proposed non-None contract and confident empty/non-list fault, no authoritative normative basis.',
    'f14': 'Unused set confused with returned effect; model wrongly requires preservation of original order instead of sorted multiplicities.',
    'f15': 'Dead branch recognized but empty-input defect fabricated; initial trigger always False, raw revised empty trigger has no violation.'
}


def main():
    root = e.ROOT
    packets = e.freeze(); cpu = e.verify_preflight()
    assert digest(packets) == cpu['packets_hash']
    e.verify_snapshot(root, 'preparation_frozen.json'); e.verify_snapshot(root, 'generation_frozen.json')
    report = json.loads((root / 'report.json').read_text()); assert e.report() == report
    status = json.loads((root / 'status.json').read_text()); assert status['exit_code'] == 0
    parent = json.loads((e.HERE / 'PARENT.json').read_text())
    assert all(hashlib.sha256((e.HERE.parent / 'v7' / n).read_bytes()).hexdigest() == sha
               for n, sha in parent['files'].items())
    artifacts, errors, fields = [], {}, Counter()
    group_costs = {}; preparation = {}
    for path in sorted((root / 'requests').glob('*.json')):
        req = json.loads(path.read_text()); art = json.loads((root / 'artifacts' / path.name).read_text())
        transport = root / 'transport/calls' / req['slot']
        raw = json.loads((transport / 'response.json').read_text())
        wire = json.loads((transport / 'wire_request.json').read_text())
        attempts = json.loads((transport / 'attempts.json').read_text())
        assert len(attempts) == 1 and attempts[0]['state'] == 'received'
        assert art['response'] == raw and raw['origin'] == 'qwen_endpoint' and raw['finish_reason'] == 'stop'
        assert req == json.loads((transport / 'request.json').read_text())
        assert art['request_hash'] == digest(req) and raw['input_tokens'] == wire['input_tokens']
        stage = req['stage']; ctx = strict_json(req['messages'][1]['content'])['context']
        errors.setdefault(stage, Counter())[art.get('reason', art['state'])] += 1
        uid, arm, _ = req['slot'].split('__')
        group = 'shared' if arm == 'shared' else arm
        cost = group_costs.setdefault(group, Counter())
        cost['calls'] += 1; cost['input_tokens'] += raw['input_tokens']; cost['output_tokens'] += raw['output_tokens']
        if stage == 'contract':
            assert set(ctx) == {'signature', 'spec'}
            obj = strict_json(raw['text'])  # Parse the ACTUAL bare JSON only; do not move any field.
            fields['contract_code_in_relation'] += obj['relation'].startswith('def obligation(')
            fields['contract_proposed'] += obj['decision'] == 'proposed'
            fields['contract_domain_Python'] += obj['domain'] == 'Python'
            fields['contract_exact_quote'] += obj['spec_quote'] in ctx['spec']
        if stage == 'behavior':
            assert set(ctx) == {'code', 'syntax'}
        if stage in ('hypothesis', 'hyp_revision'):
            obj = strict_json(raw['text'])
            if art['state'] == 'failed':
                assert 'reason' not in obj
                fields[stage + '_missing_reason'] += 1
        if stage in ('inputs', 'revision'):
            # Classify framing; do NOT strip the fence, parse its body or recover candidates.
            fields['generation_outer_markdown_fence'] += raw['text'].startswith('```json\n') and raw['text'].rstrip().endswith('```')
            if arm == 'text_hyp':
                fields['text_context_concept_null'] += ctx['unverified_model_concept'] is None
                fields['text_context_hypothesis_null'] += ctx['unverified_model_hypothesis'] is None
            if arm == 'verified_hyp':
                fields['verified_context_contract_null'] += ctx['contract'] is None
                fields['verified_context_hypothesis_null'] += ctx['hypothesis'] is None
        artifacts.append({'slot': req['slot'], 'state': art['state'], 'reason': art.get('reason'),
                          'origin': raw['origin'], 'request_hash': digest(req), 'response_hash': digest(raw),
                          'raw_text': raw['text'], 'input_tokens': raw['input_tokens'], 'output_tokens': raw['output_tokens']})
    assert len(artifacts) == 90
    rows = []
    for packet in packets:
        case = packet['case']; uid = case['fixture_id']
        prep = json.loads((root / 'preparation' / (uid + '.json')).read_text())
        generated = json.loads((root / 'generation' / (uid + '.json')).read_text())
        count = 0
        for row in prep['pool']:
            obs = observation(row['execution']); gold = fixtures.expected(case, row['arguments'])
            assert obs is not None
            count += gold is not None and not fixtures.same_observation(obs, gold)
        baseline_report = next(x for x in report['rows'] if x['case'] == uid)
        assert count == baseline_report['witness_only_bug_inputs']
        for stage in ('inputs', 'revision'):
            contexts = [strict_json(json.loads((root / 'requests' / (uid + '__' + arm + '__' + stage + '.json')).read_text())['messages'][1]['content'])['context']
                        for arm in e.ARMS]
            assert all(c['common_inputs_and_native_traces'] == prep['selection']['rows'] for c in contexts)
        for arm in e.ARMS:
            rounds = generated['arms'][arm]['rounds']
            assert len(rounds) == 2 and all(x['artifact']['state'] == 'failed' and not x['replays'] for x in rounds)
        assert prep['qualification'] == {'state': 'unqualified', 'reason': 'invalid_contract_artifact'}
        assert all(x['state'] == 'unknown' and x['reason'] == 'unqualified_contract' for x in prep['contract_checks'])
        assert prep['initial_support']['state'] == prep['final_support']['state'] == 'unverified'
        rows.append({'case': uid, 'status': 'ambiguous' if case['evaluator']['ambiguous'] else
                     'buggy' if case['evaluator']['probe_applicable'] else 'correct',
                     'pool_rows': len(prep['pool']), 'witness_only_bug_inputs': count,
                     'qualification': prep['qualification'], 'initial_support': 'unverified', 'final_support': 'unverified',
                     'accepted_LLM_inputs': 0, 'raw_rejected_generation_artifacts': 6,
                     'review': REVIEW[uid], 'source': case['source']})
    assert sum(x['witness_only_bug_inputs'] for x in rows) == 36
    assert sum(x['witness_only_bug_inputs'] > 0 for x in rows) == 3
    predicate_kinds = Counter(); evaluation_count = 0
    for p in (root / 'predicate_executions').glob('*/job.json'):
        job = json.loads(p.read_text()); result = json.loads((p.parent / 'result.json').read_text())
        predicate_kinds[job['kind']] += 1; evaluation_count += result['evaluations_attempted']
    assert predicate_kinds == {'trigger': 5} and evaluation_count == 124
    result = {'scope': 'completed frozen diagnostic9; output interface infeasible, no executable-concept efficacy comparison',
              'verification': {'source_preflight_packets_dependencies': True, 'generation_and_preparation_hashes': True,
                               'parent_v7_unchanged': True, 'raw_Qwen_origins_usage_and_single_attempts': True,
                               'spec_only_code_only_views': True, 'all9_bothround_common_evidence_parity': True,
                               'independent_witness_score_recomputation': True},
              'stage_errors': errors, 'interface_counts': fields, 'costs': report['costs'],
              'costs_by_group': group_costs, 'online_predicate_worker_kinds': predicate_kinds,
              'online_predicate_evaluations': evaluation_count,
              'wall_seconds': (dt.datetime.fromisoformat(status['finished_at']) - dt.datetime.fromisoformat(status['started_at'])).total_seconds(),
              'rows': rows, 'raw_Qwen_artifacts': artifacts,
              'semantic_review_authority': 'root and independent clean-context v24_output_review; qualitative model-assisted, not human gold',
              'false_flags_interpretation': 'zero emitted flags with zero calibration/accepted inputs; precision/effectiveness not estimable',
              'arm_realization': 'text concept null9/9 and final hypothesis null8/9; verified contract/hypothesis null9/9; intended contrast not exercised',
              'no_output_repairs_or_rescoring': True, 'Luna_probe': 'separate v23 probe, null; never pooled',
              'advance_to_benchmark': False}
    immutable(Path(__file__).with_suffix('.json'), result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'raw_Qwen_artifacts')}, indent=2))


if __name__ == '__main__':
    main()

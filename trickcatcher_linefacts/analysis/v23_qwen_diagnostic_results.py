"""Read-only verification/recomputation of frozen v23; no model or PUT execution."""
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.pipelines.v23_concepthyp import diagnostic as d
from trickcatcher_linefacts.pipelines.v23_concepthyp.diagnostic_core import (
    digest, immutable, native_observation, observation)
from trickcatcher_linefacts.pipelines.v23_concepthyp.fixture_oracles import expected

OUT = Path(__file__).with_suffix('.json')
QUALITY = {
    'f01': ('correct_no_fault', 'correct_no_fault', 'Faithful core; S2 non-list TypeError claim too strong.'),
    'f02': ('missed_fault', 'missed_fault', 'Both call returned dedup consistent with multiplicity preservation.'),
    'f03': ('correct_no_fault', 'correct_no_fault', 'S2 fabricated empty limitation; candidate count error.'),
    'f04': ('correct_fault_bad_trigger', 'correct_fault_bad_trigger', 'Both identify strict/inclusive mismatch; base trigger has no equality.'),
    'f05': ('correct_no_fault', 'correct_no_fault', 'Concept membership core retained; explicit iff/extras/duplicate invariance omitted.'),
    'f06': ('missed_fault', 'missed_fault', 'Both equate inclusion with equality after equal-set base example.'),
    'f07': ('correct_no_fault', 'false_fault', 'Direct invents missing empty-eligible guard which already exists.'),
    'f08': ('correct_fault_with_trigger', 'correct_fault_with_trigger', 'Correct None-versus-ValueError mechanism and admissible trigger.'),
    'f09': ('correct_no_fault', 'correct_no_fault', 'Concept loses explicit boolean iff/empty=True semantics.'),
    'f10': ('correct_fault_bad_trigger', 'correct_fault_bad_trigger', 'Both identify any/all; all-even trigger passes both; direct misstates empty behavior.'),
    'f11': ('false_fault', 'false_fault', 'Invented empty-list issue on correct sum comparison.'),
    'f12': ('wrong_fault_for_real_bug', 'wrong_fault_for_real_bug', 'Both ignore actual len>2 mechanism and cite empty/noninteger concerns.'),
    'f13': ('unresolved_spec_overclaim', 'unresolved_spec_overclaim', 'Undefined suitable not recorded as uncertainty; both overclaim mismatch.'),
    'f14': ('false_fault', 'false_fault', 'Both wrongly propagate unused local set into returned sorted(xs).'),
    'f15': ('false_fault', 'false_fault', 'Both invent empty defect despite recognizing unreachable dedup return.'),
    'f16': ('out_of_domain_hypothesis', 'correct_fault_with_trigger', 'Concept uses noninteger concern outside domain; direct identifies dedup with sufficient trigger.'),
}


def main():
    d.verify_preflight()
    d.verify_generation()
    root = d.ROOT
    report = json.loads((root / 'report.json').read_text())
    status = json.loads((root / 'status.json').read_text())
    assert status['exit_code'] == 0 and status['state'] == 'complete_semantic_review_pending'
    parent = json.loads((d.HERE / 'PARENT.json').read_text())
    assert all(hashlib.sha256((d.HERE.parent / 'v7' / name).read_bytes()).hexdigest() == sha
               for name, sha in parent['copied_files'].items())
    request_count = 0
    for p in (root / 'requests').glob('*.json'):
        req = json.loads(p.read_text())
        art = json.loads((root / 'artifacts' / p.name).read_text())
        transport = root / 'transport/calls' / req['slot']
        raw = json.loads((transport / 'response.json').read_text())
        wire = json.loads((transport / 'wire_request.json').read_text())
        assert art['response'] == raw and raw['origin'] == 'qwen_endpoint'
        assert raw['input_tokens'] == wire['input_tokens']
        assert art['request_hash'] == digest(req) and art['state'] == 'valid'
        assert req == json.loads((transport / 'request.json').read_text())
        context = json.loads(req['messages'][1]['content'])['context']
        if req['stage'] == 'concept':
            assert set(context) == {'signature', 'spec'}
        if req['stage'] == 'behavior':
            assert set(context) == {'code', 'syntax'}
        request_count += 1
    assert request_count == 160
    counters = {a: Counter() for a in d.ARMS}
    rows, packets = [], []
    for case in d.pilot_fixtures.cases():
        uid = case['fixture_id']
        state = json.loads((root / 'cases' / (uid + '.json')).read_text())
        gold_verdict = 'unknown' if case['evaluator']['ambiguous'] else (
            'mismatch' if case['evaluator']['probe_applicable'] else 'consistent')
        case_row = {'case': uid, 'gold_verdict': gold_verdict, 'arms': {},
                    'model_assisted_review': dict(zip(('concept_chain', 'direct_chain', 'note'), QUALITY[uid]))}
        for arm in d.ARMS:
            data = state['arms'][arm]
            c = counters[arm]
            unique, found, assertions, alarms = set(), set(), set(), set()
            hypothesis = data['hypothesis']['value']
            c['coarse_verdict_correct_cases'] += hypothesis['verdict'] == gold_verdict
            if not case['evaluator']['probe_applicable'] and gold_verdict != 'unknown':
                c['false_hypothesis_on_correct_case'] += hypothesis['verdict'] == 'mismatch'
            first_invalid = set()
            for rnd in data['rounds']:
                for item in rnd['replays']:
                    c['candidate_slots'] += 1
                    c['state_' + item['state']] += 1
                    if item['state'] == 'invalid_literal':
                        reason = item['reason']
                        c['invalid_' + reason] += 1
                        key = (item['proposal']['arguments'], reason)
                        if rnd['stage'] == 'inputs':
                            first_invalid.add(key)
                        else:
                            c['repeated_invalid_after_feedback'] += key in first_invalid
                        continue
                    if item['state'] == 'unknown':
                        c['unknown_' + item['execution']['status']] += 1
                        continue
                    literal = item['input']
                    actual = native_observation(item['execution'])
                    prediction = observation(item['proposal']['predicted_actual'])
                    model_expected = observation(item['proposal']['expected'])
                    gold = expected(case, literal)
                    c['prediction_matches_native_slots'] += prediction == actual
                    c['prediction_contradicted_native_slots'] += prediction != actual
                    if gold is None:
                        c['unscored_ambiguous_slots'] += 1
                        continue
                    unique.add(literal)
                    c['correct_expected_slots'] += model_expected == gold
                    c['incorrect_expected_slots'] += model_expected != gold
                    c['wrong_expected_equals_PUT_slots'] += model_expected != gold and model_expected == actual
                    if actual != gold:
                        found.add(literal)
                        if model_expected == gold:
                            assertions.add(literal)
                    if model_expected != gold and model_expected != actual:
                        alarms.add(literal)
            row = {'unique_scored_inputs': len(unique), 'input_discrepancies': len(found),
                   'correct_bug_assertions': len(assertions), 'false_alarm_inputs': len(alarms)}
            registered = next(r for r in report['rows'] if r['case'] == uid and r['arm'] == arm)
            assert all(registered[k] == v for k, v in row.items())
            case_row['arms'][arm] = dict(row, verdict=hypothesis['verdict'],
                                         discrepancy_inputs=sorted(found),
                                         correct_assertion_inputs=sorted(assertions),
                                         false_alarm_inputs_list=sorted(alarms))
            c['unique_scored_inputs'] += len(unique)
            c['unique_input_discrepancies'] += len(found)
            c['unique_correct_bug_assertions'] += len(assertions)
            c['unique_false_alarm_inputs'] += len(alarms)
            c['detected_bug_cases'] += bool(found)
            c['correct_assertion_cases'] += bool(assertions)
            c['false_alarm_cases'] += bool(alarms)
            c['false_alarm_on_correct_cases'] += bool(alarms) and gold_verdict == 'consistent'
        rows.append(case_row)
        packets.append({'case': uid, 'source': case['source'],
                        'concept': state['concept']['value'], 'behavior': state['behavior']['value'],
                        'hypotheses': {a: state['arms'][a]['hypothesis']['value']
                                       for a in ('concept_chain', 'direct_chain')}})
    for a, c in counters.items():
        for k in ('detected_bug_cases', 'correct_assertion_cases', 'false_alarm_cases'):
            assert c[k] == report['totals'][a][k]
    metadata = [json.loads(p.read_text()) for p in (root / 'transport/tokens').glob('*.attempts.json')]
    stage_costs = {}
    for p in (root / 'transport/calls').glob('*/response.json'):
        req = json.loads((p.parent / 'request.json').read_text())
        raw = json.loads(p.read_text())
        key = 'shared' if req['stage'] in ('concept', 'behavior') else req['slot'].split('__')[1]
        c = stage_costs.setdefault(key, Counter())
        c['calls'] += 1
        c['input_tokens'] += raw['input_tokens']
        c['output_tokens'] += raw['output_tokens']
    result = {
        'scope': 'frozen seen authored diagnostic16; no benchmark, unseen or human-gold claim',
        'verification': {'source_and_generation_hashes': True, 'source_bound_CPU_gate': True,
                         'parent_v7_unchanged': True, 'all_160_raw_origins_and_usage_checked': True,
                         'all_16_spec_only_and_code_only_preparation_views_checked': True,
                         'independent_score_recomputation_matches': True},
        'costs': report['costs'], 'costs_by_stage_group': stage_costs,
        'tokenizer_metadata_calls': sum(len(x) for x in metadata),
        'tokenizer_metadata_errors': sum(x['state'] != 'received' for xs in metadata for x in xs),
        'wall_seconds': (dt.datetime.fromisoformat(status['finished_at']) -
                         dt.datetime.fromisoformat(status['started_at'])).total_seconds(),
        'stage_counts': report['stage_counts'], 'totals': counters, 'rows': rows,
        'semantic_packets': packets,
        'semantic_review_authority': 'root plus independent clean-context v23_semantic_review; '
                                     'model-assisted qualitative labels, not independent human gold',
        'semantic_takeaway': 'Correct mechanism plus admissible sufficient trigger: concept f08; '
                             'direct f08/f16. Coarse verdict counts do not certify fault mechanism.',
        'Luna_probe': 'separate supplied-concept probe; null; never pooled',
        'advance_to_benchmark': False,
    }
    immutable(OUT, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'semantic_packets')}, indent=2))


if __name__ == '__main__':
    main()

"""Separate, exploratory supplied-concept probe; not the Qwen chain or its extraction gate."""
import argparse
import hashlib
import json
from pathlib import Path

from .diagnostic_core import (D, SCHEMAS, digest, immutable, messages, obj,
                              observation, native_observation, task_for, validate)
from .diagnostic import fixed_evidence
from .diagnostic_execution import replay_candidates
from .paths import REPO
from .pilot_fixtures import cases

ROOT = REPO / 'trickcatcher_linefacts/analysis/v23_luna_probe'
SELECTED = ('f02', 'f06', 'f12', 'f13', 'f14')
# Normative concepts only. No suspected code fault, trigger, reference output or witness.
CONCEPTS = {
    'f02': {'relation': 'Sorting preserves the multiplicity of each original occurrence.',
            'domain': 'Any list of integers.', 'uncertainty': ''},
    'f06': {'relation': 'Required membership is inclusion: every required value is present; extra container values are permitted.',
            'domain': 'Both arguments are lists of integers; repeated values do not alter membership.', 'uncertainty': ''},
    'f12': {'relation': 'The result is True if and only if the sum is at most the limit, independently of list length.',
            'domain': 'Any list of integers and an integer limit.', 'uncertainty': ''},
    'f13': {'relation': 'Return the first suitable element.', 'domain': 'A list of integers.',
            'uncertainty': 'Suitability is not defined by this spec.'},
    'f14': {'relation': 'The returned sorted copy preserves every duplicate occurrence.',
            'domain': 'Any list of integers.', 'uncertainty': ''},
}


def prepare(root=ROOT):
    source = Path(__file__).read_bytes()
    rows = {c['fixture_id']: c for c in cases()}
    for arm in ('concept', 'plain'):
        packets = []
        for uid in SELECTED:
            case = rows[uid]
            task = task_for(case)
            evidence = fixed_evidence(case, task, root)
            if not all(x['native_checked'] for x in evidence['public_base_replays']):
                raise RuntimeError('probe_requires_native_evidence')
            packet = json.loads(messages('hypothesis', task, evidence=evidence)[1]['content'])
            if arm == 'concept':
                packet['context']['supplied_normative_concept'] = CONCEPTS[uid]
            packet['instruction'] += (
                ' Also propose up to3 concrete tests that discriminate or challenge the hypothesis. '
                'Give full positional argument tuples as Python literal strings, spec-expected '
                'output and separately predicted actual output, also literal strings (or '
                'exception:TypeName). For a single argument use (value,). Unknown spec intent '
                'permits abstention with inputs=[]. Do not force a mismatch for suspicious '
                'unused code. Do not use observations as the normative expected output. '
                'Return the combined object matching the schema.')
            packet['schema'] = obj({'case': {'const': uid}, 'hypothesis': SCHEMAS['hypothesis'],
                                    'tests': SCHEMAS['inputs']})
            packets.append({'case': uid, 'request': packet})
        immutable(root / (arm + '_requests.json'), packets)
    immutable(root / 'protocol.json', {
        'source_sha256': hashlib.sha256(source).hexdigest(), 'cases': list(SELECTED),
        'model': 'gpt-6-luna', 'reasoning_effort': 'low', 'clean_context_per_arm': True,
        'authored_concepts': True, 'max_candidates_per_case': 3, 'revision': False,
        'batch_context_disclosure': 'one independent agent per arm processes5 cases; not API-stage-isolated',
        'packet_hashes': {a: digest(json.loads((root / (a + '_requests.json')).read_text()))
                          for a in ('concept', 'plain')},
        'scope': 'supplied-concept use only; no extraction reliability, Qwen result or unseen claim'})


def score(root=ROOT):
    from .fixture_oracles import expected
    from jsonschema import Draft202012Validator, ValidationError
    protocol = json.loads((root / 'protocol.json').read_text())
    rows = {c['fixture_id']: c for c in cases()}
    scores = []
    # Freeze BOTH raw agent outputs before any evaluator interpretation.
    raw = {a: json.loads((root / (a + '_response.json')).read_text()) for a in ('concept', 'plain')}
    immutable(root / 'responses_frozen.json', {a: digest(v) for a, v in raw.items()})
    for arm in ('concept', 'plain'):
        packets = json.loads((root / (arm + '_requests.json')).read_text())
        if digest(packets) != protocol['packet_hashes'][arm]:
            raise ValueError('probe_packet_drift')
        answers = raw[arm]
        if not isinstance(answers, list) or len(answers) != len(SELECTED):
            raise ValueError('probe_response_case_count')
        if {x.get('case') for x in answers} != set(SELECTED):
            raise ValueError('probe_response_case_IDs')
        by_id = {x['case']: x for x in answers}
        for packet in packets:
            uid = packet['case']
            answer = by_id[uid]
            row = {'case': uid, 'arm': arm, 'origin': 'gpt-6-luna_low_clean_context_agent'}
            task = task_for(rows[uid])
            try:
                Draft202012Validator(packet['request']['schema']).validate(answer)
                validate('hypothesis', json.dumps(answer['hypothesis']), task)
                validate('inputs', json.dumps(answer['tests']), task)
            except (ValueError, ValidationError) as exc:
                # Schema failure remains in the denominator; no answer repairs.
                row.update(state='invalid', error_type=type(exc).__name__)
                scores.append(row)
                continue
            replay = replay_candidates(task, answer['tests'], root / 'candidate_executions')
            detected, assertions, false_alarms, admissible = set(), set(), set(), set()
            for record in replay:
                if record['state'] != 'observed':
                    continue
                literal = record['input']
                admissible.add(literal)
                gold = expected(rows[uid], literal)
                if gold is None:
                    continue
                actual = native_observation(record['execution'])
                predicted = observation(record['proposal']['expected'])
                if actual != gold:
                    detected.add(literal)
                    if predicted == gold:
                        assertions.add(literal)
                if predicted != gold and predicted != actual:
                    false_alarms.add(literal)
            row.update(state='valid', hypothesis=answer['hypothesis'],
                       admissible_inputs=len(admissible), detected_inputs=len(detected),
                       correct_assertions=len(assertions), false_alarms=len(false_alarms), replays=replay)
            scores.append(row)
    result = {'scope': protocol['scope'], 'rows': scores, 'totals': {
        a: {'cases': 5, 'valid': sum(r['state'] == 'valid' for r in scores if r['arm'] == a),
            'detected_bug_cases': sum(r.get('detected_inputs', 0) > 0 for r in scores if r['arm'] == a),
            'correct_assertion_cases': sum(r.get('correct_assertions', 0) > 0 for r in scores if r['arm'] == a),
            'false_alarm_cases': sum(r.get('false_alarms', 0) > 0 for r in scores if r['arm'] == a)}
        for a in ('concept', 'plain')},
        'semantic_labels': 'raw hypotheses need independent review; executable scores cover finite submitted inputs only',
        'Qwen_calls': 0, 'benchmark_D_IO': None, 'advance_to_benchmark': False}
    immutable(root / 'report.json', result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['prepare', 'score'])
    args = p.parse_args()
    result = prepare() if args.command == 'prepare' else score()
    if result is not None:
        print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()

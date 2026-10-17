"""Run: preflight | freeze | online --online | report. No automatic benchmark expansion."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import random
import threading

from . import pilot_fixtures
from .diagnostic_core import (ARMS, D, base_inputs, digest, immutable, messages,
                              native_observation, observation, task_for, validate)
from .diagnostic_execution import execute, replay_candidates
from .paths import DATA_OUT, CONFIG

HERE = Path(__file__).resolve().parent
ROOT = DATA_OUT / 'concept_hypothesis_diagnostic'


def source_snapshot():
    return {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(HERE.rglob('*')) if p.is_file() and
            '__pycache__' not in p.parts and p.suffix in ('.py', '.json', '.md', '.jinja', '.txt')}


def freeze(root=ROOT):
    rows = pilot_fixtures.cases()
    if len(rows) != D['cases']:
        raise ValueError('fixture_count_drift')
    immutable(root / 'fixtures.json', rows)
    return immutable(root / 'protocol.json', {
        'version': CONFIG['VERSION'], 'source': source_snapshot(), 'fixtures_hash': digest(rows),
        'scope': 'seen authored diagnostic16; no benchmark/D_IO or automatic progression',
        'arms': list(ARMS), 'max_model_calls': D['max_model_calls'],
        'semantic_review': 'independent review pending; mechanical validity is not semantic correctness',
        'controls': 'concept_chain vs direct_chain tests concept-guided hypothesis+generation; '
                    'hyp_only shares the exact concept_chain hypothesis and omits explicit concept presentation',
        'costs': 'S1/S2 common preparation reported separately; not a total-cost-matched baseline claim'})


def fixed_evidence(case, task, root):
    from .diagnostic_core import syntax_evidence
    return {'syntax': syntax_evidence(task),
            'public_base_replays': [execute(task, literal, root / 'executions')
                                    for literal in base_inputs(case)],
            'scope': 'same public-base seeds for every arm; no evaluator witnesses or oracle feedback'}


def preflight(root=ROOT):
    """Real isolated executions; no model response fixtures imply semantic model success."""
    from .fixture_oracles import expected
    snapshot = source_snapshot()
    fixture_hash = digest(pilot_fixtures.cases())
    rows = []
    for case in pilot_fixtures.cases():
        task = task_for(case)
        evidence = fixed_evidence(case, task, root)
        native_ok = all(x['native_checked'] for x in evidence['public_base_replays'])
        base_ok = all(expected(case, x['input']) in (None, native_observation(x))
                      for x in evidence['public_base_replays'])
        witness = case['evaluator']['witness']
        discrepancy = None
        if witness is not None:
            output = execute(task, witness, root / 'preflight_evaluator_only')
            discrepancy = (output['native_checked'] and expected(case, witness) is not None
                           and expected(case, witness) != native_observation(output))
        rows.append({'case': case['fixture_id'], 'native_checked': native_ok,
                     'base_agrees_with_spec_or_unknown': base_ok,
                     'authored_bug_witness_discrepancy': discrepancy})
    result = {'scope': 'CPU only; no model/concept efficacy claim', 'rows': rows,
              'source': snapshot, 'fixtures_hash': fixture_hash,
              'passed': all(r['native_checked'] and r['base_agrees_with_spec_or_unknown'] and
                            r['authored_bug_witness_discrepancy'] is not False for r in rows)}
    # CPU gates may be rerun during code review BEFORE source freeze. Preserve each
    # source-bound attempt rather than reusing a stale gate or editing old evidence.
    path = root / 'preflight.json'
    if path.exists():
        old = json.loads(path.read_text())
        immutable(root / 'preflight_attempts' / (digest(old.get('source')) + '.json'), old)
    immutable(root / 'preflight_attempts' / (digest(snapshot) + '.json'), result)
    from .diagnostic_client import write_json
    write_json(path, result)
    return result


def verify_preflight(root=ROOT):
    path = root / 'preflight.json'
    if not path.exists():
        raise ValueError('passing_CPU_preflight_required')
    result = json.loads(path.read_text())
    if (not result['passed'] or result.get('source') != source_snapshot()
            or result.get('fixtures_hash') != digest(pilot_fixtures.cases())):
        raise ValueError('CPU_preflight_failed_or_source_drift')
    return result


def slot(case_id, stage, arm='shared'):
    return case_id + '__' + arm + '__' + stage


def run(client, root=ROOT):
    """A single locked controller; failures stay in the full fixture denominator."""
    freeze(root)
    if (root / 'generation_frozen.json').exists():
        verify_generation(root)
        return
    cases = list(pilot_fixtures.cases())
    random.Random(D['seed']).shuffle(cases)

    def ask(case, task, stage, arm='shared', **kwargs):
        request = {'slot': slot(case['fixture_id'], stage, arm), 'stage': stage,
                   'seed': D['seed'] + int(case['fixture_id'][1:]),
                   'task_hash': task['task_hash'], 'messages': messages(stage, task, **kwargs)}
        path = root / 'artifacts' / (request['slot'] + '.json')
        immutable(root / 'requests' / (request['slot'] + '.json'), request)
        if len(list((root / 'requests').glob('*.json'))) > D['max_model_calls']:
            raise RuntimeError('logical_call_budget')
        if path.exists():
            return json.loads(path.read_text())
        from .diagnostic_client import SlotFailure
        try:
            response = client.complete(request)
        except SlotFailure as exc:
            return immutable(path, {'request_hash': digest(request), 'state': 'failed',
                                    'failure_kind': 'transport_or_context', 'reason': str(exc)})
        record = {'request_hash': digest(request), 'response': response}
        if response.get('finish_reason') != 'stop':
            record.update(state='failed', reason='incomplete_finish_reason')
        else:
            try:
                record.update(state='valid', value=validate('inputs' if stage == 'revision' else stage,
                                                           response['text'], task))
            except ValueError as exc:
                record.update(state='failed', reason=str(exc))
        immutable(path, record)
        return record

    def usable(record):
        return record is not None and record.get('state') == 'valid'

    for case in cases:
        task = task_for(case)
        evidence = fixed_evidence(case, task, root)
        # Native evidence is an explicit feasibility prerequisite, not silently unverified text.
        if not all(x['native_checked'] for x in evidence['public_base_replays']):
            raise RuntimeError('native_execution_preflight_required')
        immutable(root / 'evidence' / (case['fixture_id'] + '.json'), evidence)
        concept = ask(case, task, 'concept')
        behavior = ask(case, task, 'behavior')
        hyps = {}
        for arm in ('concept_chain', 'direct_chain'):
            if not usable(behavior) or (arm == 'concept_chain' and not usable(concept)):
                hyps[arm] = None
                continue
            hyps[arm] = ask(case, task, 'hypothesis', arm,
                            concept=concept['value'] if arm == 'concept_chain' else None,
                            behavior=behavior['value'], evidence=evidence)
        hyps['hyp_only'] = hyps['concept_chain']  # exact hypothesis, no semantic rewrite
        # Fixed seeded order avoids always placing the concept branch first.
        order = list(ARMS)
        random.Random(D['seed'] + int(case['fixture_id'][1:])).shuffle(order)
        summaries = {}
        for arm in order:
            hyp = hyps[arm]
            if not usable(hyp):
                summaries[arm] = {'state': 'blocked_upstream', 'hypothesis': hyp, 'rounds': []}
                continue
            kwargs = {'hypothesis': hyp['value'], 'behavior': behavior['value'], 'evidence': evidence,
                      'concept': concept['value'] if arm == 'concept_chain' else None}
            first = ask(case, task, 'inputs', arm, **kwargs)
            rounds = [{'stage': 'inputs', 'artifact': first, 'replays': []}]
            if usable(first):
                rounds[0]['replays'] = replay_candidates(task, first['value'], root / 'executions')
                second = ask(case, task, 'revision', arm, previous=first['value'],
                             feedback=rounds[0]['replays'], **kwargs)
                rounds.append({'stage': 'revision', 'artifact': second,
                               'replays': replay_candidates(task, second['value'], root / 'executions')
                               if usable(second) else []})
            summaries[arm] = {'state': 'completed', 'hypothesis': hyp, 'rounds': rounds}
        immutable(root / 'cases' / (case['fixture_id'] + '.json'),
                  {'case': case['fixture_id'], 'concept': concept, 'behavior': behavior, 'arms': summaries})
        print(case['fixture_id'], {a: summaries[a]['state'] for a in ARMS}, flush=True)
    files = [p for name in ('requests', 'artifacts', 'cases', 'evidence', 'executions')
             for p in (root / name).rglob('*.json')]
    immutable(root / 'generation_frozen.json', {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                               for p in sorted(files)})


def verify_generation(root=ROOT):
    freeze(root)
    snapshot = json.loads((root / 'generation_frozen.json').read_text())
    for name, sha in snapshot.items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != sha:
            raise ValueError('generation_drift:' + name)


def report(root=ROOT):
    """Evaluator import happens only after generation is frozen and verified."""
    if not (root / 'generation_frozen.json').exists():
        freeze(root)
        return incomplete_summary(root)
    verify_generation(root)
    from .fixture_oracles import expected
    packets, scores = [], []
    for case in pilot_fixtures.cases():
        state = json.loads((root / 'cases' / (case['fixture_id'] + '.json')).read_text())
        task = task_for(case)
        evidence = fixed_evidence(case, task, root)
        common = {x['input'] for x in evidence['public_base_replays']}
        for arm, data in state['arms'].items():
            unique, found, assertions, false_alarms = set(), set(), set(), set()
            unknown = 0
            for rnd in data['rounds']:
                for row in rnd['replays']:
                    if row['state'] != 'observed':
                        unknown += 1
                        continue
                    literal = row['input']
                    gold = expected(case, literal)
                    if gold is None:
                        unknown += 1
                        continue
                    unique.add(literal)
                    actual = native_observation(row['execution'])
                    predicted_expected = observation(row['proposal']['expected'])
                    if actual != gold:
                        found.add(literal)
                        if predicted_expected == gold:
                            assertions.add(literal)
                    if predicted_expected != gold and predicted_expected != actual:
                        false_alarms.add(literal)
            stage_states = {r['stage']: r['artifact']['state'] for r in data['rounds']}
            if 'inputs' not in stage_states:
                stage_states['inputs'] = 'blocked_upstream'
            if 'revision' not in stage_states:
                stage_states['revision'] = 'blocked_upstream'
            failed_stages = sum(s == 'failed' for s in stage_states.values())
            abstentions = sum(r['artifact']['state'] == 'valid' and not r['artifact']['value']['inputs']
                              for r in data['rounds'])
            scores.append({'case': case['fixture_id'], 'arm': arm,
                           'unique_scored_inputs': len(unique), 'input_discrepancies': len(found),
                           'correct_bug_assertions': len(assertions), 'false_alarm_inputs': len(false_alarms),
                           'new_input_discrepancies': len(found - common),
                           'unknown_or_invalid_slots': unknown, 'blocked': data['state'] == 'blocked_upstream',
                           'stage_states': stage_states, 'failed_input_stages': failed_stages,
                           'valid_abstention_stages': abstentions})
        packets.append({'case': case['fixture_id'], 'source': case['source'],
                        'evaluator': case['evaluator'], 'model_artifacts': state,
                        'review': 'pending independent semantic review; do not infer semantic accuracy from schema pass'})
    totals = {}
    for arm in ARMS:
        rows = [s for s in scores if s['arm'] == arm]
        totals[arm] = {'fixtures': len(rows), 'detected_bug_cases': sum(s['input_discrepancies'] > 0 for s in rows),
                       'correct_assertion_cases': sum(s['correct_bug_assertions'] > 0 for s in rows),
                       'false_alarm_cases': sum(s['false_alarm_inputs'] > 0 for s in rows),
                       'blocked_cases': sum(s['blocked'] for s in rows),
                       'failed_input_stages': sum(s['failed_input_stages'] for s in rows),
                       'valid_abstention_stages': sum(s['valid_abstention_stages'] for s in rows)}
    stage_counts = {}
    for p in (root / 'requests').glob('*.json'):
        req = json.loads(p.read_text())
        artifact = json.loads((root / 'artifacts' / p.name).read_text())
        stage = req['stage']
        stage_counts.setdefault(stage, {'valid': 0, 'failed': 0})[artifact['state']] += 1
    result = {'scope': 'seen authored diagnostic16, not benchmark D_IO or general concept gain',
              'totals': totals, 'rows': scores, 'advance_to_benchmark': False,
              'semantic_review': 'pending', 'stage_counts': stage_counts, 'costs': costs(root)}
    immutable(root / 'review_packets.json', packets)
    immutable(root / 'report.json', result)
    return result


def incomplete_summary(root=ROOT, error_type=None):
    """Full denominator without scoring unfrozen partial generation or repairing treatment."""
    rows = []
    for case in pilot_fixtures.cases():
        path = root / 'cases' / (case['fixture_id'] + '.json')
        rows.append({'case': case['fixture_id'], 'state': 'generation_recorded' if path.exists()
                     else 'incomplete_or_not_started'})
    return {'scope': 'incomplete diagnostic; no final efficacy scoring', 'state': 'incomplete',
            'fixtures': len(rows), 'rows': rows, 'error_type': error_type,
            'costs': costs(root), 'advance_to_benchmark': False}


def costs(root=ROOT):
    rows = []
    for p in (root / 'transport' / 'calls').glob('*/attempts.json'):
        request = json.loads((p.parent / 'request.json').read_text())
        for row in json.loads(p.read_text()):
            rows.append(dict(row, stage=request['stage']))
    return {'physical_completion_attempts': len(rows),
            'input_tokens': sum(r.get('input_tokens', 0) for r in rows),
            'output_tokens': sum(r.get('output_tokens', 0) for r in rows),
            'unknown_usage_attempts': sum(r['state'] != 'received' for r in rows),
            'shared_preparation_attempts': sum(r['stage'] in ('concept', 'behavior') for r in rows),
            'generation_requests': len(list((root / 'requests').glob('*.json'))),
            'cost_scope': 'common preparation separate; no total-cost-matched efficacy claim'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['preflight', 'freeze', 'online', 'report'])
    parser.add_argument('--online', action='store_true', help='explicit endpoint opt-in; default never contacts a model')
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'controller.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('diagnostic_controller_already_running')
        if args.command == 'preflight':
            result = preflight()
        elif args.command == 'freeze':
            result = freeze()
        elif args.command == 'report':
            result = report()
        else:
            if not args.online:
                raise SystemExit('online_requires_explicit_--online')
            verify_preflight()
            freeze()
            from .diagnostic_client import Client
            client = Client(ROOT / 'transport')
            stop = threading.Event()
            def ping():
                while not stop.wait(1200):
                    try:
                        client.call('/models', timeout=8)
                    except Exception:
                        pass
            threading.Thread(target=ping, daemon=True).start()
            try:
                run(client)
                result = report()
            except Exception as exc:
                from .diagnostic_client import write_json
                write_json(ROOT / 'incomplete_status.json', incomplete_summary(error_type=type(exc).__name__))
                raise SystemExit('diagnostic_incomplete:' + type(exc).__name__) from None
            finally:
                stop.set()
                client.close()
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

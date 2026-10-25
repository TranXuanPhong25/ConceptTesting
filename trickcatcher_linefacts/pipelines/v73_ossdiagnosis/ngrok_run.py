"""One shared semantic-writer call, CPU construction, matched 3-call generator arms.

Ngrok only, serial/resumable. This runner generates and replays observations, never scores
against a private oracle. Independent evaluation follows its immutable generation freeze.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import time
import tempfile
import fcntl

from .construction import replay
from .deep_run import manifest, prepare, proposal_request, validate_request
from .hypotheses import import_proposals
from .ngrok_client import EndpointError, NgrokClient, json_object
from .bindings import resolve

HERE = Path(__file__).resolve().parent
ARMS = ('plain', 'concept', 'equal_evidence_raw', 'inputs_only')
MAX_PROMPT_CHARACTERS=64000


def write_new(path, value):
    """Publish a fully flushed artifact atomically, refusing overwrite."""
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.pending-', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2, ensure_ascii=True)
            stream.flush(); os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def read_record(path):
    try: return json.loads(Path(path).read_text())
    except (ValueError, OSError): raise ValueError('artifact_unreadable:' + Path(path).name) from None


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def call(client, directory, messages, stage, seed, max_tokens):
    directory.mkdir(parents=True, exist_ok=True)
    identity = dict(messages=messages, stage=stage, seed=seed, max_tokens=max_tokens, model=client.model, provider='ngrok')
    dest = directory / 'response.json'
    if dest.exists():
        record = read_record(dest)
        if record['request_sha256'] != digest(identity): raise ValueError('cached_request_drift')
        if record['error'] == 'transport_attempt_budget_exhausted': raise EndpointError('transport_attempt_budget_exhausted')
        return record
    request_path = directory / 'request.json'
    if request_path.exists():
        if read_record(request_path) != identity: raise ValueError('partial_request_drift')
    else: write_new(request_path, identity)
    if len(json.dumps(messages)) > MAX_PROMPT_CHARACTERS:
        record = dict(request_sha256=digest(identity), error='prompt_character_cap', response=None, value=None)
    else:
        token_path = directory / 'tokenization.json'
        if token_path.exists(): token_info = read_record(token_path)
        else:
            token_info = client.tokenize(messages)
            write_new(token_path, token_info)
        if token_info['count'] + max_tokens > token_info['max_model_len']:
            record = dict(request_sha256=digest(identity), error='context_budget_exceeded', response=None, value=None)
            write_new(dest, record)
            return record
        attempts = sorted(directory.glob('attempt_??.json'))
        received = directory / f'attempt_{len(attempts):02d}_result.json'
        recovered = read_record(received) if attempts and received.exists() else None
        if recovered and recovered.get('status') == 'received' and 'response' in recovered:
            response = recovered['response']
        elif len(attempts) >= 2:
            record = dict(request_sha256=digest(identity), error='transport_attempt_budget_exhausted', response=None, value=None)
            write_new(dest, record)
            raise EndpointError('transport_attempt_budget_exhausted')
        else:
            attempt = len(attempts) + 1
            attempt_path = directory / f'attempt_{attempt:02d}.json'
            # An interrupted/in-flight request is charged as an unknown completion, never a free retry.
            write_new(attempt_path, dict(request_sha256=digest(identity), attempt=attempt,
                                        status='dispatched_completion_unknown'))
            try: response = client.complete(messages, max_tokens=max_tokens, seed=seed)
            except EndpointError as exc:
                write_new(directory / f'attempt_{attempt:02d}_result.json', dict(status='transport_failed', error=str(exc)))
                raise
            write_new(directory / f'attempt_{attempt:02d}_result.json', dict(status='received', response=response))
        error = None; value = None
        if response['finish_reason'] != 'stop': error = 'incomplete_completion'
        else:
            try: value = json_object(response['content'])
            except (ValueError, TypeError): error = 'invalid_json_object'
        record = dict(request_sha256=digest(identity), error=error, response=response, value=value)
    write_new(dest, record)
    return record


def compact_arm(prepared, arm):
    prompt = dict(prepared['prompts'][arm])
    if arm == 'inputs_only':
        shown = compact_arm(prepared, 'concept')['evidence']
        prompt['inputs'] = list(dict.fromkeys(x['arguments'] for h in shown for x in h['inputs']))
        prompt['input_display_limit'] = dict(max_hypotheses=3, max_inputs_per_hypothesis=2)
        return prompt
    if 'evidence' not in prompt: return prompt
    slim = []
    for row in prompt['evidence'][:3]:
        h = row['hypothesis']
        entry = {key: row[key] for key in ('rank', 'hypothesis', 'base_status', 'construction_status', 'limitations')}
        entry['inputs'] = []
        for x in row['inputs'][:2]:
            entry['inputs'].append({key: x[key] for key in ('arguments', 'predicted_put', 'predicted_alternative', 'put_path', 'alternative_path', 'verification', 'domain')})
        slim.append(entry)
    prompt['evidence'] = slim
    prompt['evidence_display_limit'] = dict(max_hypotheses=3, max_inputs_per_hypothesis=2,
                                          omitted_hypotheses=max(0, len(prepared['prompts'][arm]['evidence']) - 3),
                                          full_formulas_available_in_cpu_artifact=True)
    return prompt


def generate_case(client, request, folder, config):
    folder.mkdir(parents=True, exist_ok=True)
    result_file = folder / 'case_result.json'
    case_identity = digest(dict(input_manifest=manifest(request, config), model=client.model))
    if result_file.exists():
        old = read_record(result_file)
        if old.get('case_input_identity') != case_identity: raise ValueError('case_result_drift')
        return old
    writer = proposal_request(request)
    writer['instruction'] += ' Return {"hypotheses": [...], "summary": "..."}, at most three hypotheses.'
    tree = ast.parse(request['source']); entry_fn, _ = resolve(tree, request['entry'])
    writer['eligible_sites'] = [{'span': [n.lineno, n.col_offset, n.end_lineno, n.end_col_offset], 'before': ast.unparse(n)}
                               for n in ast.walk(entry_fn) if isinstance(n, (ast.Compare, ast.BinOp, ast.Call, ast.AugAssign, ast.Subscript))][:48]
    system = 'Return one JSON object only. Tool outputs are observations, not correct expected outputs. Respect the specification input domain.'
    shared = call(client, folder / 'hypothesis', [{'role': 'system', 'content': system}, {'role': 'user', 'content': json.dumps(writer)}],
                  'hypothesis', 20261024, 1536)
    raw = (shared.get('value') or {}).get('hypotheses', [])
    accepted, rejected = [], []
    if not isinstance(raw, list): raw = []; rejected.append(dict(error='hypotheses_not_list'))
    if len(raw) > 3: rejected.append(dict(error='hypothesis_cap', omitted=len(raw) - 3))
    for index, proposal in enumerate(raw[:3]):
        try:
            import_proposals(request['source'], request['entry'], [proposal], spec=request.get('spec'))
            accepted.append(proposal)
        except (ValueError, TypeError, KeyError, SyntaxError) as exc:
            rejected.append(dict(index=index, error=type(exc).__name__ + ':' + str(exc)[:200]))
    enriched = dict(request, proposals=accepted)
    cpu_path = folder / 'cpu_prepared.json'
    if cpu_path.exists():
        cpu = json.loads(cpu_path.read_text())
        if cpu['manifest'] != manifest(enriched, config): raise ValueError('cpu_manifest_drift')
        prepared = cpu['result']
    else:
        prepared = prepare(enriched, config)
        write_new(cpu_path, dict(manifest=manifest(enriched, config), result=prepared))
    contexts = {arm: compact_arm(prepared, arm) for arm in ARMS}
    assert contexts['concept'].get('evidence') == contexts['equal_evidence_raw'].get('evidence')
    record = dict(case_id=request['case_id'], case_input_identity=case_identity, accepted_hypotheses=len(accepted), rejected_hypotheses=rejected,
                  shared_call_charged_to_all_arms=True, arms={}, scope='generation_and_PUT_observations_only')
    record['witness_only'] = [dict(example=e, observation=replay(request['source'], request['entry'], ast.literal_eval(e['arguments']), None))
                              for e in request['public_examples']]
    schema = {'tests': [{'arguments': '(all positional values,)', 'expected': 'Python literal',
                         'hypothesis_id': 'optional identifier', 'trigger_explanation': 'why this input exercises the obligation'}], 'reason': 'brief explanation'}
    for arm in ARMS:
        history = []
        for round_index in range(3):
            stage = 'final' if round_index == 2 else 'probe'
            content = dict(context=contexts[arm], earlier_feedback=history, output_schema=schema,
                           instruction=('Give up to six final tests.' if stage == 'final' else 'Propose up to six tests; PUT observations will be returned.'))
            messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': json.dumps(content)}]
            response = call(client, folder / arm / stage if stage == 'final' else folder / arm / f'probe{round_index + 1}',
                            messages, stage, 20261024 + round_index, 1536)
            tests = (response.get('value') or {}).get('tests', [])
            feedback = []; invalid = []
            if not isinstance(tests, list): tests = []; invalid.append('tests_not_list')
            for index, test in enumerate(tests[:6]):
                try:
                    args = ast.literal_eval(test['arguments']); ast.literal_eval(test['expected'])
                    if type(args) is not tuple or len(repr(args)) > 4000: raise ValueError('argument_tuple_or_size')
                    observation = replay(request['source'], request['entry'], args, None)
                    observed = observation.get('put', {'status': observation['status']})
                    feedback.append(dict(arguments=test['arguments'], expected=test['expected'],
                                         put_observation={k: observed[k] for k in ('status', 'output', 'reason') if k in observed}))
                except (ValueError, TypeError, KeyError, SyntaxError) as exc:
                    invalid.append(dict(index=index, error=type(exc).__name__))
            history.append(dict(stage=stage, response_error=response['error'], invalid=invalid, feedback=feedback))
        record['arms'][arm] = dict(rounds=history, final=history[-1])
    write_new(result_file, record)
    return record


def main():
    # Keep the historical transport helpers, but never launch the inherited v57
    # generation path under v65's name without the new evidence gate.
    from .pipeline import main as integrated_main
    integrated_main()


if __name__ == '__main__': main()

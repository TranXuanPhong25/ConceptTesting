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
from .value_graph import show

HERE = Path(__file__).resolve().parent
ARMS = ('plain', 'concept', 'equal_evidence_raw', 'inputs_only')
SYSTEM = 'Return one JSON object only. Tool outputs are observations, not correct expected outputs. Respect the specification input domain.'


def EVALUATION_SOURCES():
    """Scorer files pinned in the protocol before any generation; drift blocks private scoring."""
    root = HERE.parents[1]
    files = [root / 'analysis/v68_symbolicgen/score_v68.py', root / 'pipelines/v60_pathfault_complete/score_worker.py',
             root / 'pipelines/v63_scopeguard/frozen_score.py', root / 'pipelines/v63_scopeguard/literal_contract.py']
    return {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


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
    if len(json.dumps(messages)) > 24000:
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


def candidate_inputs(prepared, cap=12):
    """Distinct verified inputs in evidence rank order; beyond the cap they are not judged and not shown."""
    seen = []
    for row in prepared['prompts']['concept']['evidence']:
        for x in row['inputs']:
            if x['arguments'] not in seen: seen.append(x['arguments'])
    return seen[:cap]


def filter_evidence(evidence, valid, judged):
    kept = []
    for row in evidence:
        r = dict(row); r['inputs'] = [x for x in row['inputs'] if x['arguments'] in valid]
        r['inputs_hidden_judged_invalid'] = sum(1 for x in row['inputs'] if x['arguments'] in judged and x['arguments'] not in valid)
        r['inputs_hidden_not_judged'] = sum(1 for x in row['inputs'] if x['arguments'] not in judged)
        kept.append(r)
    # Stable: hypotheses with a spec-judged-valid verified witness first, original order otherwise.
    return sorted(kept, key=lambda r: not r['inputs'])


def clip(text, limit=300):
    return text if len(text) <= limit else text[:limit] + '...<truncated>'


def compact_arm(prepared, arm, valid, judged=frozenset()):
    prompt = dict(prepared['prompts'][arm])
    if arm == 'inputs_only':
        shown = compact_arm(prepared, 'concept', valid, judged)['evidence']
        prompt['inputs'] = list(dict.fromkeys(x['arguments'] for h in shown for x in h['inputs']))
        prompt['input_display_limit'] = 'same inputs as shown in the concept/raw evidence'
        return prompt
    if 'evidence' not in prompt: return prompt
    evidence = filter_evidence(prompt['evidence'], valid, judged)
    # Context guard (8192 tokens incl. 1536 output): shrink display until evidence <= 3000 chars; same for concept/raw.
    for hyps, per in ((3, 2), (2, 2), (2, 1), (1, 1)):
        slim = display(evidence, hyps, per)
        if len(json.dumps(slim)) <= 3000: break
    prompt['evidence'] = slim
    prompt['evidence_display_limit'] = dict(max_hypotheses=hyps, max_inputs_per_hypothesis=per,
                                          omitted_hypotheses=max(0, len(evidence) - hyps),
                                          full_constraints_available_in_cpu_artifact=True)
    return prompt


def display(evidence, hyps, per):
    slim = []
    for row in evidence[:hyps]:
        entry = {key: row[key] for key in ('rank', 'base_status', 'construction_status', 'inputs_hidden_judged_invalid', 'inputs_hidden_not_judged')}
        # Compact hypothesis view (8192-token context); full record stays in cpu_prepared.json.
        entry['hypothesis'] = {k: row['hypothesis'][k] for k in ('id', 'family', 'meaning', 'span', 'before', 'after', 'origin', 'objective',
                                                                 'rationale', 'spec_quote', 'trigger_reason') if k in row['hypothesis']}
        entry['limitations'] = row['limitations'][:3]
        entry['inputs'] = [dict(arguments=clip(x['arguments']), put_output=clip(show(x['symbolic_put_output'])),
                                alternative_output=clip(show(x['symbolic_alternative_output'])), verification=x['verification'])
                           for x in row['inputs'][:per]]
        slim.append(entry)
    return slim


def cpu_stage(client, request, folder, config):
    """Shared writer call (cache-reusable) and CrossHair preparation; no generator calls."""
    folder.mkdir(parents=True, exist_ok=True)
    writer = proposal_request(request)
    writer['instruction'] += ' Return {"hypotheses": [...], "summary": "..."}, at most three hypotheses.'
    tree = ast.parse(request['source']); entry_fn, _ = resolve(tree, request['entry'])
    writer['eligible_sites'] = [{'span': [n.lineno, n.col_offset, n.end_lineno, n.end_col_offset], 'before': ast.unparse(n)}
                               for n in ast.walk(entry_fn) if isinstance(n, (ast.Compare, ast.BinOp, ast.Call, ast.AugAssign, ast.Subscript))][:48]
    shared = call(client, folder / 'hypothesis', [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': json.dumps(writer)}],
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
    return accepted, rejected, prepared


def generate_case(client, request, folder, config):
    folder.mkdir(parents=True, exist_ok=True)
    result_file = folder / 'case_result.json'
    case_identity = digest(dict(input_manifest=manifest(request, config), model=client.model))
    if result_file.exists():
        old = read_record(result_file)
        if old.get('case_input_identity') != case_identity: raise ValueError('case_result_drift')
        return old
    system = SYSTEM
    accepted, rejected, prepared = cpu_stage(client, request, folder, config)
    candidates = candidate_inputs(prepared)
    validity = dict(candidates=candidates, judged_valid=[], response_error=None)
    if candidates:
        judge = dict(instruction=('Decide for each input whether it satisfies ALL input constraints stated in the specification '
                                  '(types, lengths, value ranges, character sets, structural preconditions). Do not judge outputs. '
                                  'Return {"valid": [true or false for each input, in order]}.'),
                     spec=request.get('spec', ''), entry=request['entry'],
                     inputs=[dict(index=i, arguments=a) for i, a in enumerate(candidates)])
        response = call(client, folder / 'validity', [{'role': 'system', 'content': system}, {'role': 'user', 'content': json.dumps(judge)}],
                        'validity', 20261025, 512)
        verdict = (response.get('value') or {}).get('valid')
        validity['response_error'] = response['error']
        # Fail closed: a malformed verdict shows no constructed inputs.
        if isinstance(verdict, list) and len(verdict) == len(candidates):
            validity['judged_valid'] = [a for a, v in zip(candidates, verdict) if v is True]
        else:
            validity['response_error'] = validity['response_error'] or 'verdict_shape'
    valid = set(validity['judged_valid'])
    contexts = {arm: compact_arm(prepared, arm, valid, frozenset(candidates)) for arm in ARMS}
    assert contexts['concept'].get('evidence') == contexts['equal_evidence_raw'].get('evidence')
    record = dict(case_id=request['case_id'], case_input_identity=case_identity, accepted_hypotheses=len(accepted), rejected_hypotheses=rejected, validity=validity,
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
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['metadata', 'run', 'prepare-cpu'])
    p.add_argument('--case')
    p.add_argument('--model', default='qwen2.5-coder-32b-instruct')
    p.add_argument('--requests', type=Path)
    p.add_argument('--out', type=Path)
    a = p.parse_args()
    try:
        if a.command == 'prepare-cpu':
            # Offline CPU stage only: the writer slot must already be cached; no endpoint is contacted.
            class Offline:
                model = a.model
                def tokenize(self, *_): raise EndpointError('offline_cpu_stage_requires_cached_writer')
                complete = tokenize
            config = json.loads((HERE / 'config.json').read_text())['symbolicpath']
            request = next(r for r in json.loads(a.requests.read_text()) if r['case_id'] == a.case)
            validate_request(request)
            accepted, rejected, prepared = cpu_stage(Offline(), request, a.out / str(request['case_id']), config)
            print(json.dumps(dict(case_id=request['case_id'], accepted=len(accepted), rejected=len(rejected), statuses=prepared['status_counts'])), flush=True)
            return
        client = NgrokClient(); metadata = client.metadata()
        if a.command == 'metadata': print(json.dumps(metadata)); return
        if not a.requests or not a.out: raise ValueError('requests_and_out_required')
        raw = a.requests.read_text()
        try:
            parsed = json.loads(raw)
            requests = [parsed] if isinstance(parsed, dict) else parsed
        except ValueError:
            requests = [json.loads(line) for line in raw.splitlines() if line.strip()]
        if not isinstance(requests, list): raise ValueError('request_list_or_object_required')
        if not 1 <= len(requests) <= 6: raise ValueError('pilot_case_cap_1_to_6')
        for request in requests: validate_request(request)
        if len({r['case_id'] for r in requests}) != len(requests): raise ValueError('duplicate_case_id')
        # case_id is used as a directory name: forbid traversal and separators.
        if any(not str(r['case_id']).replace('-', '').replace('_', '').isalnum() for r in requests): raise ValueError('case_id')
        config = json.loads((HERE / 'config.json').read_text())['symbolicpath']
        protocol = dict(metadata=metadata, inputs=[manifest(r, config) for r in requests], arms=list(ARMS),
                        construction_backend='crosshair 0.0.112 (v66)', shared_validity_calls=1,
                        writer_slots_reused_from='v57 generation_v2 (identical request identity checked per slot)',
                        evaluation_sources=EVALUATION_SOURCES(),
                        shared_writer_calls=1, generator_calls_per_arm=3, max_tests_per_call=6,
                        max_tokens_per_call=1536, max_prompt_chars=24000, serial=True, private_scoring=False,
                        max_transport_attempts_per_slot=2, max_chat_attempts=28 * len(requests),
                        tokenization_preflight='server /tokenize, exact prompt+output <= context; no chat dispatch if exceeded')
        a.out.mkdir(parents=True, exist_ok=True)
        run_lock = (a.out / '.run.lock').open('a')
        try: fcntl.flock(run_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('another_runner_owns_this_output') from None
        protocol_path = a.out / 'protocol.json'
        if protocol_path.exists():
            if json.loads(protocol_path.read_text()) != protocol: raise ValueError('protocol_drift')
        else: write_new(protocol_path, protocol)
        freeze = a.out / 'generation_frozen.json'
        if freeze.exists():
            print('generation_already_frozen'); return
        for r in requests:
            result = generate_case(client, r, a.out / str(r['case_id']), config)
            print(json.dumps(dict(case_id=r['case_id'], accepted_hypotheses=result['accepted_hypotheses'], arms=list(result['arms']))), flush=True)
        files = {str(f.relative_to(a.out)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(a.out.rglob('*.json'))}
        write_new(freeze, files)
        print('generation_frozen_no_private_score', flush=True)
    except (EndpointError, ValueError) as exc:
        # EndpointError messages intentionally contain status/type only, never URL or key.
        print(json.dumps(dict(status='stopped', error=str(exc))), flush=True)
        raise SystemExit(2) from None


if __name__ == '__main__': main()

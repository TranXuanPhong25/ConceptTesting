"""Bounded paired Qwen contract diagnostic. No canonical loading/reference execution or efficacy scoring."""
import argparse
import collections
import fcntl
import hashlib
import json
import os
from pathlib import Path
import threading
import time

from trickcatcher_linefacts.pipelines.v21_flowtools import flow_client as live, flow_tools as old_tools
from trickcatcher_linefacts.pipelines.v21_flowtools import flow_packages as old_packages, flow_run as views
from trickcatcher_linefacts.pipelines.v21_flowtools import flow_trace as old_trace, flow_cfg as old_cfg
from trickcatcher_linefacts.pipelines.v30_flowcontract import flow_tools as new_tools, flow_packages as new_packages
from trickcatcher_linefacts.pipelines.v30_flowcontract import flow_trace as new_trace, flow_cfg as new_cfg, source_view, tool_contract
from trickcatcher_linefacts.pipelines.v30_flowcontract.flow_common import digest, immutable

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OLD = REPO / 'trickcatcher_linefacts/pipelines/v21_flowtools'
NEW = REPO / 'trickcatcher_linefacts/pipelines/v30_flowcontract'
PARENT = REPO / 'trickcatcher_linefacts/out/pipelines/v21_flowtools/humaneval/flowrun/pilot20'
ROOT = REPO / 'trickcatcher_linefacts/out/v30_contract_diagnostic/paired10'
CASES = ('0', '43', '70', '77', '84', '90', '105', '131', '82', '116')
ARMS = ('old_contract', 'repaired_contract')


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    live.write_json(path, value)


def sources():
    result = {}
    for folder in (OLD, NEW, HERE):
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.suffix in ('.py', '.json', '.jinja'):
                result[str(p.relative_to(REPO))] = sha(p)
    result[str((HERE / 'PREREG.md').relative_to(REPO))] = sha(HERE / 'PREREG.md')
    return result


def cfg_equivalent(a, b):
    # networkx Graph equality is object identity; compare the serialized structure/attributes instead.
    if {k: v for k, v in a.items() if k != 'graph'} != {k: v for k, v in b.items() if k != 'graph'}:
        return False
    ga, gb = a.get('graph'), b.get('graph')
    if ga is None or gb is None:
        return ga is gb
    return dict(ga.nodes(data=True)) == dict(gb.nodes(data=True)) and sorted(ga.edges(data=True)) == sorted(gb.edges(data=True))


def packet(cid, bundle):
    shared = read(PARENT / 'cases' / cid / 'shared.json')
    candidates = sorted((PARENT / 'cases' / cid).glob('arms/*/executions/*/job.json'))
    if not candidates:
        raise ValueError('missing_frozen_worker_source')
    job = read(candidates[0])
    t = bundle[int(cid)]
    task = source_view.prepare(job['source'], job['entry'], t['base'], valid_code=t['mined_valid_src'])
    anchor = next((PARENT / 'cases' / cid).glob('arms/*/tools/ledger.json'))
    if read(anchor)['context']['task_hash'] != task['task_hash']:
        raise ValueError('parent_task_hash_mismatch')
    if not cfg_equivalent(old_cfg.build(task), new_cfg.build(task)):
        raise ValueError('old_new_CFG_mismatch')
    if sha(OLD / 'flow_trace.py') != sha(NEW / 'flow_trace.py'):
        raise ValueError('old_new_projection_code_mismatch')
    ledger = PARENT / 'cases' / cid / 'common/ledger.json'
    traces = {}
    if ledger.exists():
        for e in read(ledger)['events']:
            internal = e['result'].get('internal')
            if internal and internal['trace_id'].startswith('C'):
                traces[internal['trace_id']] = internal
    for witness in shared['common']:
        if witness.get('status') == 'ok' and witness['trace'] not in traces:
            raise ValueError('missing_common_trace')
    return dict(case=cid, task=task, concepts=shared['concepts'], hypotheses=shared['hypotheses'],
                common=shared['common'], common_traces=traces, parent_shared_sha256=sha(PARENT / 'cases' / cid / 'shared.json'))


def prepare(root=ROOT):
    frozen = read(PARENT / 'generation_frozen.json')
    for rel, expected in frozen.items():
        path = (PARENT / rel).resolve()
        if PARENT.resolve() not in path.parents or sha(path) != expected:
            raise ValueError('parent_generation_hash_mismatch')
    old_protocol = read(PARENT / 'protocol.json')
    if any(sha(OLD / name) != h for name, h in old_protocol['sources'].items()):
        raise ValueError('parent_source_hash_mismatch')
    rows = read(REPO / 'trickcatcher_linefacts/out/pipelines/v7/humaneval/tasks_hybrid.json')['tasks']
    bundle = {t['task']: t for t in rows}
    packets = [packet(cid, bundle) for cid in CASES]
    protocol = dict(cases=list(CASES), arms=list(ARMS), arm_order=[list(ARMS if i % 2 == 0 else ARMS[::-1]) for i in range(len(CASES))],
                    sources=sources(), packet_sha256={p['case']: digest(p) for p in packets},
                    parent_manifest_sha256=sha(PARENT / 'generation_frozen.json'),
                    slots=60, completion_attempt_ceiling=180, completion_output_token_ceiling=51200,
                    seed='20261019 + 100*case_id + stage_index', mode='selected_seen_interface_diagnostic_no_oracle',
                    model='qwen2.5-coder-7b-instruct', context=16384, temperature=0, top_p=1)
    immutable(root / 'protocol.json', protocol)
    for p in packets:
        immutable(root / 'packets' / (p['case'] + '.json'), p)
    return packets, protocol


def message(stage, ctx):
    return views.message(views.INSTR[stage], ctx, stage)


def old_history(history):
    if len(json.dumps(history, ensure_ascii=False)) > 12000:
        return [dict(round=h['round'], feedback=h['feedback'][:3], omitted=max(0, len(h['feedback']) - 3)) for h in history]
    return history


def make_session(p, arm, root):
    module = old_tools if arm == 'old_contract' else new_tools
    s = module.FlowSession(p['task'], root / 'cases' / p['case'] / arm / 'tools', arm='agent-tools')
    s.adopt(p['common_traces'])
    return s


def context(p, session, arm):
    packages = old_packages if arm == 'old_contract' else new_packages
    package = packages.build('agent-tools', session, concepts=p['concepts'], hypotheses=p['hypotheses'], witnesses=p['common'])
    return dict(views.original_context(p['task']), guidance=package['sections'], tool_protocol=packages.TOOL_PROTOCOL)


def paired_context_assertion(p, root):
    a = context(p, make_session(p, ARMS[0], root), ARMS[0])
    b = context(p, make_session(p, ARMS[1], root), ARMS[1])
    for c in (a, b):
        c.pop('tool_protocol')
        c['guidance'].pop('tools')
    if a != b:
        raise ValueError('arm_context_diff_outside_contract')


def run_arm(p, arm, root, client):
    done = root / 'cases' / p['case'] / arm / 'result.json'
    if done.exists():
        return read(done)
    session = make_session(p, arm, root)
    ctx = context(p, session, arm)
    record = dict(case=p['case'], arm=arm, calls=[], rounds=[], final=None, final_executions=[])
    history = []
    for stage_index in (1, 2, 3):
        stage = 'agent' if stage_index < 3 else 'final'
        prompt = message(stage, dict(ctx, earlier_feedback=history))
        request = dict(slot=f'{p["case"]}/{arm}/{stage_index}', stage=stage,
                       seed=20261019 + 100 * int(p['case']) + stage_index, messages=prompt)
        response = client.complete(request)
        error, value = None, None
        try:
            if response.get('finish_reason') == 'length':
                raise ValueError('truncated_response')
            value = views.validate(stage, response['text'])
        except ValueError as exc:
            error = str(exc)[:160]
        record['calls'].append(dict(stage_index=stage_index, slot=request['slot'], error=error,
                                    input_tokens=response['input_tokens'], output_tokens=response['output_tokens']))
        if stage == 'final':
            record['final'] = value
            if value is not None:
                record['final_executions'] = session.final_inputs([t['arguments'] for t in value['tests']])
        else:
            session.begin_round()
            feedback = [session.view(session.act(a)) for a in value['actions']] if value is not None else [dict(status='reply_invalid', error=error)]
            record['rounds'].append(dict(round=stage_index, value=value, feedback=feedback))
            history.append(dict(round=stage_index, feedback=feedback))
            history = old_history(history) if arm == 'old_contract' else tool_contract.project_history(history)
    record['tool_report'] = session.report()
    immutable(done, record)
    return record


def instrument_workers(root):
    """Durable reservation ledger around unchanged sandbox calls; no change to worker inputs/results."""
    for module in (old_tools, new_tools):
        original = module.sandbox

        def tracked(*args, _original=original, **kwargs):
            path = root / 'native_attempts.json'
            ledger = read(path) if path.exists() else []
            if len(ledger) >= 840:
                raise ValueError('native_process_budget_exhausted')
            number = len(ledger)
            ledger.append(dict(number=number + 1, state='reserved_unknown', job_sha256=sha(Path(args[2]))))
            write(path, ledger)
            try:
                result = _original(*args, **kwargs)
            except BaseException as exc:
                ledger[number].update(state='failed', error_type=type(exc).__name__)
                write(path, ledger)
                raise
            ledger[number]['state'] = 'returned'
            write(path, ledger)
            return result
        module.sandbox = tracked


def freeze(root):
    files = [root / 'protocol.json']
    for folder in ('cases', 'packets', 'transport'):
        files.extend((root / folder).rglob('*.json'))
    for name in ('native_attempts.json', 'metadata_events.json', 'launches.json'):
        if (root / name).exists():
            files.append(root / name)
    manifest = {str(p.relative_to(root)): sha(p) for p in sorted(files)}
    return immutable(root / 'generation_frozen.json', manifest)


def verify_freeze(root):
    for rel, h in read(root / 'generation_frozen.json').items():
        if sha(root / rel) != h:
            raise ValueError('generation_freeze_drift')


def is_id_cap_error(action, result):
    return (isinstance(action.get('ids'), list) and len(action['ids']) > 4 and result.get('status') == 'error'
            and (result.get('error') == 'ids_shape_or_count' or
                 (result.get('error') == 'action_schema:maxItems' and result.get('error_details', {}).get('field') == '/ids')))


def report(root):
    summary = {}
    for arm in ARMS:
        counts = collections.Counter()
        cases = []
        for cid in CASES:
            path = root / 'cases' / cid / arm / 'result.json'
            if not path.exists():
                continue
            rec = read(path)
            counts['completed_cases'] += 1
            counts['valid_calls'] += sum(c['error'] is None for c in rec['calls'])
            counts['reply_errors'] += sum(c['error'] is not None for c in rec['calls'])
            signatures = []
            rejected_first = []
            corrected_second = []
            for round in rec['rounds']:
                actions = (round['value'] or {}).get('actions', [])
                for action, result in zip(actions, round['feedback']):
                    counts['actions'] += 1
                    counts['tool:' + str(action.get('tool'))] += 1
                    counts['action_errors'] += result.get('status') != 'ok'
                    counts['submitted_over_cap_ids'] += isinstance(action.get('ids'), list) and len(action['ids']) > 4
                    if result.get('status') == 'error':
                        counts['error:' + result.get('error', 'unspecified')] += 1
                        counts['id_cap_errors'] += is_id_cap_error(action, result)
                    if round['round'] == 1 and is_id_cap_error(action, result):
                        rejected_first.append(action)
                    if round['round'] == 2 and result.get('status') == 'ok':
                        for earlier in rejected_first:
                            if (earlier.get('tool') == action.get('tool') and isinstance(earlier.get('ids'), list)
                                    and len(earlier['ids']) > 4 and isinstance(action.get('ids'), list)
                                    and 0 < len(action['ids']) <= 4 and all(x in earlier['ids'] for x in action['ids'])):
                                corrected_second.append(action)
                                break
                    counts['hypothesis_links'] += bool(action.get('hypothesis'))
                    signatures.append(digest(action))
            counts['repeated_queries'] += len(signatures) - len(set(signatures))
            counts['cases_with_candidate_cap_correction'] += bool(corrected_second)
            counts['final_admissible'] += sum(x.get('domain_filter') == 'accepted' for x in rec['final_executions'])
            counts['final_native_checked'] += sum(bool(x.get('native_checked')) for x in rec['final_executions'])
            cases.append(dict(case=cid, actions=rec['tool_report']['actions'], errors=rec['tool_report']['errors'],
                              candidate_cap_corrections=corrected_second))
        summary[arm] = dict(counts=counts, cases=cases)
    attempts, received, tokens_in, tokens_out, unknown = 0, 0, 0, 0, 0
    for path in (root / 'transport/calls').rglob('attempts.json'):
        ledger = read(path)
        attempts += len(ledger)
        unknown += sum(x['state'] != 'received' for x in ledger)
    for path in (root / 'transport/calls').rglob('response.json'):
        response = read(path)
        received += 1
        tokens_in += response['input_tokens']
        tokens_out += response['output_tokens']
    slots = []
    for cid in CASES:
        for arm in ARMS:
            for stage in (1, 2, 3):
                matching = list((root / 'transport/calls' / cid / arm / str(stage)).glob('request.json'))
                if len(matching) > 1:
                    raise ValueError('multiple_requests_for_scheduled_slot')
                state = 'not_attempted'
                if matching:
                    d = matching[0].parent
                    state = ('response_received' if (d / 'response.json').exists() else
                             'completion_failed_usage_unknown' if (d / 'attempts.json').exists() else 'precompletion_failed')
                slots.append(dict(case=cid, arm=arm, stage=stage, state=state))
    native = read(root / 'native_attempts.json') if (root / 'native_attempts.json').exists() else []
    metadata = read(root / 'metadata_events.json') if (root / 'metadata_events.json').exists() else []
    tokenizer_attempts = sum(len(read(p)) for p in (root / 'transport/tokens').glob('*.attempts.json'))
    result = dict(scope='selected seen paired interface diagnostic; no detection/semantic-gate claim', arms=summary,
                  scheduled_slots=60, received=received, not_received=60-received, physical_attempts=attempts,
                  usage_unknown_attempts=unknown, input_tokens=tokens_in, output_tokens=tokens_out, slots=slots,
                  tokenizer_attempts=tokenizer_attempts, native_process_attempts=len(native),
                  native_process_unknown=sum(x['state'] == 'reserved_unknown' for x in native),
                  metadata_requests_reserved=len(metadata), keepalive_requests=sum(x['kind'] == 'keepalive' for x in metadata))
    write(root / 'report.json', result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'run'))
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        packets, protocol = prepare()
        for p in packets:
            paired_context_assertion(p, ROOT)
        if (ROOT / 'generation_frozen.json').exists():
            verify_freeze(ROOT)
            report(ROOT)
            print('Completed generation freeze verified; no new requests')
            return
        if args.command == 'prepare':
            write(ROOT / 'status.json', dict(state='prepared_waiting_endpoint', cases=10, scheduled_slots=60, completions=0))
            print('Prepared10 paired cases/60 slots; no model calls')
            return
        if not os.environ.get('QWEN_BASE_URL'):
            raise SystemExit('QWEN_BASE_URL_missing; prepared run preserved')
        stop = threading.Event()
        client = None
        keeper = None
        status = dict(state='running', started=time.time(), scheduled_slots=60, metadata_requests=1, keepalive_requests=0)
        write(ROOT / 'status.json', status)
        previous = read(ROOT / 'launches.json') if (ROOT / 'launches.json').exists() else []
        previous.append(dict(started=status['started'], metadata_requests_reserved=1))
        write(ROOT / 'launches.json', previous)
        metadata = read(ROOT / 'metadata_events.json') if (ROOT / 'metadata_events.json').exists() else []
        metadata.append(dict(kind='preflight', state='reserved'))
        write(ROOT / 'metadata_events.json', metadata)
        try:
            instrument_workers(ROOT)
            client = live.Client(ROOT / 'transport')
            metadata[-1]['state'] = 'received'
            write(ROOT / 'metadata_events.json', metadata)
            def keepalive():
                while not stop.wait(1200):
                    status['keepalive_requests'] += 1
                    metadata.append(dict(kind='keepalive', state='reserved'))
                    write(ROOT / 'metadata_events.json', metadata)
                    try:
                        client.call('/models', timeout=8)
                        metadata[-1]['state'] = 'received'
                    except Exception:
                        metadata[-1]['state'] = 'failed'
                    write(ROOT / 'metadata_events.json', metadata)
            keeper = threading.Thread(target=keepalive, daemon=True)
            keeper.start()
            for i, p in enumerate(packets):
                for arm in protocol['arm_order'][i]:
                    try:
                        run_arm(p, arm, ROOT, client)
                    except (live.ProtocolFailure, live.SlotFailure):
                        raise
                    except Exception as exc:
                        immutable(ROOT / 'cases' / p['case'] / arm / 'failure.json', dict(type=type(exc).__name__, state='arm_failure'))
                        raise
                    print('case', p['case'], arm, 'finished', flush=True)
            if not all((ROOT / 'cases' / cid / arm / 'result.json').exists() for cid in CASES for arm in ARMS):
                raise ValueError('missing_terminal_arm_records')
            status['state'] = 'complete'
        except Exception as exc:
            status.update(state='stopped_preflight_or_transport', error_type=type(exc).__name__)
        finally:
            stop.set()
            if keeper is not None:
                keeper.join(timeout=10)
            if client is not None:
                client.close()
            status['finished'] = time.time()
            if status['state'] == 'complete':
                freeze(ROOT)
                verify_freeze(ROOT)
            else:
                # Partial snapshots are diagnostic only; they must not block unchanged missing-work resume.
                write(ROOT / 'partial_snapshot.json', {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'cases').rglob('*.json'))})
            metrics = report(ROOT)
            status['received'] = metrics['received']
            write(ROOT / 'status.json', status)
        print(json.dumps(status), flush=True)


if __name__ == '__main__':
    main()

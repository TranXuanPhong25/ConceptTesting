"""Frozen 8-initial +16 paired full-revision diagnostic. No native worker imports."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

from . import revision_protocol as protocol
from .d1_client import Client, InputOverCap, TransportStop
from .flow_common import strict_json, digest, immutable, write_json
from .paths import HERE, REPO, DATA_OUT

ROOT = DATA_OUT / 'revision8'
OLD = REPO / 'trickcatcher_linefacts/out/pipelines/v43_concept_identify/humaneval/binding8'
QUOTA = REPO / 'trickcatcher_linefacts/analysis/astra_concept_design_20261020/quota_guard.py'
EVALUATION = REPO / 'trickcatcher_linefacts/analysis/v50_binding_revision_20261023/EVALUATION.md'
EPISODES = (3, 6, 2, 8, 4, 1, 5, 7)
SLOTS = [f'E{i}__{stage}' for i in EPISODES for stage in ('initial', 'final_raw', 'final_tool')]


def read(path):
    return strict_json(Path(path).read_text(), max_bytes=32*1024*1024)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def files(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(Path(root).rglob('*'))
            if p.is_file() and p.suffix != '.pyc' and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}


def sources():
    return files(HERE)


def dependencies():
    return {'python': sys.version, 'python_sha256': sha(Path(sys.executable).resolve()),
            'installed': dict(sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions())),
            'quota_helper_sha256': sha(QUOTA)}


def parents(full=False):
    inventory = read(OLD/'terminal_inventory.json')
    if full:
        actual = {str(p.relative_to(OLD)): sha(p) for p in OLD.rglob('*') if p.is_file() and p.name != 'terminal_inventory.json'}
        if actual != inventory:
            raise ValueError('v43_terminal_drift')
        frozen = read(OLD/'freeze.json')
        if files(HERE.parent/'v43_concept_identify') != frozen['sources']:
            raise ValueError('v43_source_drift')
        prior = REPO/'trickcatcher_linefacts/out/pipelines/v40_concept_agent/humaneval'
        for name, expected in frozen['parent_inventories'].items():
            if sha(prior/name/'terminal_inventory.json') != expected:
                raise ValueError('v40_inventory_identity_drift')
            old_files = {str(p.relative_to(prior/name)): sha(p) for p in (prior/name).rglob('*')
                         if p.is_file() and p.name != 'terminal_inventory.json'}
            if old_files != read(prior/name/'terminal_inventory.json'):
                raise ValueError('v40_parent_content_drift')
    return {'v43_terminal': sha(OLD/'terminal_inventory.json'), 'v43_freeze': sha(OLD/'freeze.json')}


def approval_matches(root, kind):
    approval = read(root/f'{kind}_approval.json')
    if approval.get('passed') is not True or approval.get('sources') != sources():
        raise ValueError('independent_source_approval_required')
    review = (REPO/approval['review_path']).resolve()
    if REPO not in review.parents or sha(review) != approval['review_sha256']:
        raise ValueError('review_identity_drift')
    if approval.get('evaluation_sha256') != sha(EVALUATION):
        raise ValueError('evaluation_approval_required')
    return approval


def prepare(root=ROOT):
    approval_matches(root, 'preparation')
    parent = parents(full=True)
    for i in range(1, 9):
        p = OLD/'prepared'/f'E{i}.json'
        row = read(p)
        if sha(p) != read(OLD/'freeze.json')['prepared'][p.name]:
            raise ValueError('parent_pool_drift')
        immutable(root/'prepared'/p.name, row)
    immutable(root/'freeze.json', {'sources': sources(), 'dependencies': dependencies(), 'parents': parent,
                                  'prepared': files(root/'prepared'), 'slots': SLOTS,
                                  'evaluation_sha256': sha(EVALUATION),
                                  'preparation_approval_sha256': sha(root/'preparation_approval.json')})


def verify(root=ROOT, full=False):
    freeze = read(root/'freeze.json')
    if freeze['sources'] != sources() or freeze['dependencies'] != dependencies():
        raise ValueError('source_dependency_drift')
    if freeze['parents'] != parents(full=full) or freeze['prepared'] != files(root/'prepared'):
        raise ValueError('parent_or_pool_drift')
    if freeze['slots'] != SLOTS or freeze['preparation_approval_sha256'] != sha(root/'preparation_approval.json'):
        raise ValueError('approval_or_slots_drift')
    if freeze['evaluation_sha256'] != sha(EVALUATION):
        raise ValueError('evaluation_drift')
    approval_matches(root, 'preparation')


def quota(root=ROOT):
    done = subprocess.run([sys.executable, str(QUOTA), 'check'], capture_output=True, text=True, timeout=30, check=True)
    snapshot = strict_json(done.stdout)
    checks = root/'quota_checks'
    immutable(checks/f'{len(list(checks.glob("*.json"))):05d}.json', snapshot)
    write_json(root/'quota_latest.json', snapshot)
    remaining = snapshot.get('remaining_percent')
    if type(remaining) not in (int, float) or remaining <= 15 or snapshot.get('should_stop') is not False:
        raise TransportStop('quota_at_or_below15_or_unknown')
    return snapshot


def slots(root):
    result = {}
    for slot in SLOTS:
        artifact = root/'artifacts'/f'{slot}.json'
        attempt = root/'transport/calls'/slot/'attempt.json'
        if artifact.exists():
            record = read(artifact)
            admission = record['admission']
            result[slot] = {'state': 'input_over_cap' if record['raw'] is None else 'received',
                            'envelope_valid': admission['envelope_valid'],
                            'admitted_items': len(admission['accepted'])}
        elif attempt.exists():
            result[slot] = {'state': 'attempted_without_artifact', 'attempt': read(attempt)}
        else:
            result[slot] = {'state': 'not_attempted'}
    return result


def complete(client, root, slot, packet, final=False):
    verify(root)
    quota(root)
    messages = [{'role': 'system', 'content': 'Return one JSON object. Bind requirements from spec. '
                 'Observed implementation behavior does not establish a normative requirement.'},
                {'role': 'user', 'content': json.dumps(packet, ensure_ascii=False)}]
    immutable(root/'requests'/f'{slot}.json', messages)
    try:
        response = client.complete(slot, messages)
    except InputOverCap as exc:
        # Local token cap: nothing sent, packet not shortened; slot fails, run continues.
        record = {'raw': None, 'admission': protocol.unavailable('input_over_cap'),
                  'input_over_cap': {'input_tokens': exc.count, 'cap': exc.cap, 'http_sent': False}}
    else:
        record = {'raw': response, 'admission': protocol.admit(response, final, packet.get('evidence_ids', []))}
    immutable(root/'artifacts'/f'{slot}.json', record)
    write_json(root/'slots.json', slots(root))
    return record


def run(root=ROOT):
    verify(root, full=True)
    approval = approval_matches(root, 'launch')
    if approval.get('freeze_sha256') != sha(root/'freeze.json'):
        raise ValueError('launch_freeze_mismatch')
    window = approval.get('endpoint_window', {})
    if window.get('exclusive') is not True or not window.get('competing_owners_checked'):
        raise ValueError('shared_endpoint_window_required')
    expiry = datetime.fromisoformat(window['expires_utc'])
    if expiry.tzinfo is None or datetime.now(timezone.utc) >= expiry:
        raise ValueError('endpoint_window_expired')
    # One byte read is archived and hashed; non-UTF-8 approvals fail before any state change.
    approval_bytes = (root/'launch_approval.json').read_bytes()
    approval_text = approval_bytes.decode('utf-8')
    status_path = root/'status.json'
    checkpoints = sorted((root/'checkpoints').glob('*.json'))
    if status_path.exists() or checkpoints or (root/'launches').exists():
        if not status_path.exists() or not checkpoints:
            raise ValueError('resume_state_incomplete')
        old = read(status_path)
        if old.get('state') != 'stopped' or old.get('reason') != 'quota_at_or_below15_or_unknown':
            raise ValueError('terminal_run_no_automatic_retry')
        checkpoint = read(checkpoints[-1])
        if checkpoint['state'] != old:
            raise ValueError('status_checkpoint_mismatch')
        current = {k: v for k, v in files(root).items() if not k.startswith('checkpoints/')}
        expected = dict(checkpoint['files'])
        old_approval = expected.get('launch_approval.json')
        if old_approval != current.get('launch_approval.json'):
            # Renew only the endpoint window, preserving predecessor bytes. approval_matches
            # above still pins exact sources, review and rubric; freeze_sha256 pins freeze.
            prior = None
            for path, fingerprint in expected.items():
                if path.startswith('launches/') and current.get(path) == fingerprint:
                    record = read(root/path)
                    text = record.get('approval_json')
                    if (type(text) is str and record.get('approval_sha256') == old_approval
                            and hashlib.sha256(text.encode('utf-8')).hexdigest() == old_approval):
                        prior = strict_json(text)
            if prior is None:
                raise ValueError('prior_launch_approval_not_archived')
            outside = lambda value: {k: v for k, v in value.items() if k != 'endpoint_window'}
            if outside(prior) != outside(approval):
                raise ValueError('renewal_changes_more_than_window')
            if expiry <= datetime.fromisoformat(prior['endpoint_window']['expires_utc']):
                raise ValueError('renewal_window_not_later')
            expected['launch_approval.json'] = current.get('launch_approval.json')
        if expected != current:
            raise ValueError('quota_checkpoint_drift')
    state = {'state': 'running', 'started_utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid()}
    write_json(status_path, state)
    client = None
    try:
        # Archive this launch's approval before anything that can stop the run.
        launch_id = f'launch{len(list((root/"launches").glob("*.json")))}'
        immutable(root/'launches'/f'{launch_id}.json', {'started_utc': state['started_utc'],
                  'approval_sha256': hashlib.sha256(approval_bytes).hexdigest(),
                  'approval_json': approval_text})
        quota(root)
        def before_http():
            verify(root)
            quota(root)
            if datetime.now(timezone.utc) >= expiry:
                raise TransportStop('endpoint_window_expired')
        client = Client(root/'transport', before_request=before_http, preflight_id=launch_id)
        for i in EPISODES:
            if datetime.now(timezone.utc) >= expiry:
                raise TransportStop('endpoint_window_expired')
            row = read(root/'prepared'/f'E{i}.json')
            initial = complete(client, root, f'E{i}__initial', protocol.initial_packet(row))
            feedback = protocol.compare_feedback(initial['admission']['accepted'], row)
            immutable(root/'feedback'/f'E{i}.json', feedback)
            arms = ('raw', 'tool') if i % 2 else ('tool', 'raw')
            for arm in arms:
                # Endpoint-window expiry is checked before each possible network call.
                if datetime.now(timezone.utc) >= expiry:
                    raise TransportStop('endpoint_window_expired')
                final = complete(client, root, f'E{i}__final_{arm}', protocol.final_packet(row, initial, feedback, arm), True)
                immutable(root/'transitions'/f'E{i}__{arm}.json',
                          protocol.transitions(initial['admission']['accepted'], final['admission']['accepted']))
        immutable(root/'generation_frozen.json', {name: files(root/name) for name in
                  ('prepared', 'requests', 'artifacts', 'feedback', 'transitions', 'transport')})
        verify(root, full=True)
        state['state'] = 'complete'
    except BaseException as exc:
        state.update(state='stopped', error_type=type(exc).__name__,
                     reason=str(exc) if isinstance(exc, TransportStop) else 'controller_failure')
    finally:
        if client:
            client.close()
        state['ended_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(root/'slots.json', slots(root))
        write_json(status_path, state)
        snapshot = {k: v for k, v in files(root).items() if not k.startswith('checkpoints/')}
        checkpoint_id = len(list((root/'checkpoints').glob('*.json')))
        immutable(root/'checkpoints'/f'{checkpoint_id:04d}.json',
                  {'state': state, 'files': snapshot, 'slots': slots(root)})
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare', 'verify', 'run'])
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT/'controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = {'prepare': prepare, 'verify': verify, 'run': run}[args.command]()
    if result is not None:
        print(json.dumps(result))


if __name__ == '__main__':
    main()

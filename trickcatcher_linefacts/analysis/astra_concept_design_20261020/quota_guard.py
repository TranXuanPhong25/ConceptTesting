"""Read-only Codex quota RPC; optional user-authorized one-shot continuation timer.

Never prints account identifiers, authentication data, credit offers, or endpoints.
Does not make a model turn unless the scheduled continuation fires after reset.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import select
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
STATE = REPO / 'trickcatcher_linefacts/out/agent_schedules/astra_d1_qwen32b'


def quota():
    proc = subprocess.Popen(['codex', 'app-server', '--stdio'], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
    def send(data):
        proc.stdin.write(json.dumps(data) + '\n')
        proc.stdin.flush()
    try:
        send({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
              'params': {'clientInfo': {'name': 'quota_readonly', 'version': '1.0'},
                         'capabilities': {'experimentalApi': True}}})
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if not select.select([proc.stdout], [], [], 1)[0]:
                continue
            line = proc.stdout.readline()
            if not line:
                break
            data = json.loads(line)
            if data.get('id') == 1:
                if 'error' in data:
                    raise RuntimeError('quota_initialization_failed')
                send({'jsonrpc': '2.0', 'method': 'initialized'})
                send({'jsonrpc': '2.0', 'id': 2, 'method': 'account/rateLimits/read', 'params': {}})
            elif data.get('id') == 2:
                if 'error' in data:
                    raise RuntimeError('quota_read_failed')
                raw = data['result']
                limits = raw.get('rateLimitsByLimitId', {}).get('codex', raw.get('rateLimits', {}))
                window = limits.get('primary') or {}
                if window.get('windowDurationMins') != 300 or type(window.get('usedPercent')) not in (int, float):
                    raise RuntimeError('five_hour_window_unavailable')
                remaining = max(0, 100 - window['usedPercent'])
                return {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                        'window_minutes': 300, 'remaining_percent': remaining,
                        'reset_unix': window.get('resetsAt'),
                        'ordinary_usage_allowed': raw.get('ordinaryUsageAllowed'),
                        'stop_at_percent': 15,
                        'should_stop': remaining <= 15 or raw.get('ordinaryUsageAllowed') is False}
        raise RuntimeError('quota_read_timeout')
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def schedule(snapshot, thread_id):
    """One timer only, for this same user-authorized task after the reported reset."""
    if not snapshot['should_stop']:
        raise RuntimeError('quota_threshold_not_reached')
    reset = snapshot.get('reset_unix')
    if type(reset) not in (int, float):
        raise RuntimeError('quota_reset_time_unavailable')
    when = max(time.time() + 60, reset + 120)
    STATE.mkdir(parents=True, exist_ok=True)
    path = STATE / 'schedule.json'
    if path.exists():
        prior = json.loads(path.read_text())
        if prior['state'] == 'scheduled':
            return prior
        if prior['state'] in ('resuming', 'continuation_exited'):
            path.rename(STATE / ('consumed_' + prior['unit'] + '.json'))
        else:
            raise RuntimeError('existing_schedule_requires_review:' + prior['state'])
    if not thread_id:
        raise RuntimeError('current_thread_unavailable')
    unit = 'concept-astra-d1-qwen32b-' + str(int(when)) + '-15'
    # State is private local runtime; the endpoint itself is never stored here.
    state = {'state': 'reserved', 'unit': unit, 'thread_id': thread_id,
             'wake_unix': when, 'wake_utc': datetime.fromtimestamp(when, timezone.utc).isoformat(),
             'quota': snapshot, 'task': 'same authorized Astra D1 diagnostic; no duplicate launch or provider fallback'}
    path.write_text(json.dumps(state, indent=2) + '\n')
    calendar = datetime.fromtimestamp(when, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    command = ['systemd-run', '--user', '--unit=' + unit, '--on-calendar=' + calendar,
               '--timer-property=AccuracySec=5s', '--property=WorkingDirectory=' + str(REPO),
               '--property=StandardOutput=append:' + str(STATE / 'continuation.log'),
               '--property=StandardError=append:' + str(STATE / 'continuation.log'),
               '/usr/bin/python3', str(HERE / 'quota_guard.py'), 'wake']
    done = subprocess.run(command, capture_output=True, text=True)
    if done.returncode:
        state.update(state='failed', error='systemd_timer_creation_failed')
        path.write_text(json.dumps(state, indent=2) + '\n')
        raise RuntimeError(state['error'])
    state['state'] = 'scheduled'
    path.write_text(json.dumps(state, indent=2) + '\n')
    return state


def wake():
    path = STATE / 'schedule.json'
    state = json.loads(path.read_text())
    snapshot = quota()
    if snapshot['should_stop']:
        state.update(state='still_below_threshold', wake_quota=snapshot)
        path.write_text(json.dumps(state, indent=2) + '\n')
        # A fresh one-shot timer at the new reset; preserve this consumed schedule.
        path.rename(STATE / ('consumed_' + state['unit'] + '.json'))
        schedule(snapshot, state['thread_id'])
        return
    prompt = (
        'Resume the existing user-authorized Astra concept diagnostic task in /home/phong/dev/ConceptTester. '
        'Read AGENTS.md, shared memory, analysis/astra_concept_design_20261020 and runtime schedule state. '
        'User authorized implementing/auditing then running the small D1 diagnostic with exact '
        'qwen2.5-coder-32b-instruct on the endpoint in their last authorization message; keep URL only '
        'in environment, never files/logs. Check live Codex5h quota with quota_guard.py before sustained '
        'work and between phases; if remaining<=15%, checkpoint and schedule next reset again. '
        'Preserve other sessions files and all frozen versions/runs. Do not duplicate launch, reset '
        'unknown attempts, use paid fallback, train, or expand benchmark/heldout. Finish Astra design '
        'review, new-version implementation, CPU checks and clean-context audit, preregister/freeze '
        'before any Qwen task call. Inspect existing run status before any launch. Once authorized '
        'D1 completes/stops, independently review actual outputs, report all episodes/controls/costs '
        'and limits in Vietnamese, update own RESULTS/memory, commit/push own files main. '
        'This scheduled wake continues the same task, not permission for a new experiment.'
    )
    state.update(state='resuming', wake_quota=snapshot)
    path.write_text(json.dumps(state, indent=2) + '\n')
    completed = subprocess.run(['codex', 'exec', 'resume', '--skip-git-repo-check', state['thread_id'], prompt],
                               cwd=REPO, stdin=subprocess.DEVNULL)
    state.update(state='continuation_exited', returncode=completed.returncode)
    current = json.loads(path.read_text()) if path.exists() else None
    destination = path if current and current.get('unit') == state['unit'] else STATE / ('consumed_' + state['unit'] + '.json')
    destination.write_text(json.dumps(state, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('check', 'schedule', 'wake'))
    args = parser.parse_args()
    if args.command == 'wake':
        wake()
    else:
        snapshot = quota()
        if args.command == 'check':
            print(json.dumps(snapshot))
        else:
            state = schedule(snapshot, os.environ.get('CODEX_THREAD_ID'))
            print(json.dumps({k: state[k] for k in ('state', 'unit', 'wake_utc')}))

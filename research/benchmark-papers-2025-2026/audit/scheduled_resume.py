"""Resume this authorized audit at the user's reset slots, serially and quota-aware."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess

AUDIT = Path(__file__).resolve().parent
REPO = AUDIT.parents[2]


def main():
    if (AUDIT / 'COMPLETE.json').exists():
        print('Audit complete; no continuation started.')
        return
    config = json.loads((AUDIT / 'scheduler_config.json').read_text())
    lock = (AUDIT / 'runner.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('An audit continuation is already running; skip overlap.')
        return
    lease = AUDIT / 'foreground_lease.json'
    if lease.exists():
        active_until = datetime.fromisoformat(json.loads(lease.read_text())['active_until'])
        if active_until > datetime.now(timezone.utc):
            print('Foreground audit lease active; no duplicate continuation.')
            return
    session_files = list(Path('/home/phong/.codex/sessions').glob(f'**/*{config["thread_id"]}*.jsonl'))
    latest = None
    for path in sorted(session_files, key=lambda p: p.stat().st_mtime):
        with path.open() as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                rates = event.get('payload', {}).get('rate_limits')
                if rates:
                    latest = rates
    now = datetime.now(timezone.utc).timestamp()
    if latest:
        for label, threshold in [('primary', 90), ('secondary', 98)]:
            rate = latest.get(label) or {}
            if rate.get('used_percent', 0) >= threshold and rate.get('resets_at', 0) > now:
                state = {'checked_at': datetime.now(timezone.utc).isoformat(), 'status': 'await_quota_reset',
                         'window': label, 'used_percent': rate.get('used_percent'), 'resets_at': rate.get('resets_at')}
                (AUDIT / 'scheduler_status.json').write_text(json.dumps(state, indent=2))
                print(f'{label} quota requires reset; continuation deferred.')
                return
    prompt = ('Continue the user-authorized 500-paper full-text/public-source audit. Read '
              'research/benchmark-papers-2025-2026/audit/CONTINUE.md and audit/STATUS.md first. '
              'Append verified results to REPORT.md and root PAPER_AUDIT_500_REPORT.md. Read and '
              'verify unreviewed papers until near quota, then checkpoint. Preserve previous reviews '
              'and source code. No paid model calls, reimplementations, parallel agents, branches or '
              'unsolicited commits. Report actual counts; downloaded text is not read. '
              'Use the same inherited model. Stop scheduling when COMPLETE.json exists.')
    env = dict(os.environ)
    # Only the existing ChatGPT account login is authorized for this continuation.
    for key in ('OPENAI_API_KEY', 'CODEX_API_KEY'):
        env.pop(key, None)
    logs = AUDIT / 'runlogs'
    logs.mkdir(exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    state = {'started_at': datetime.now(timezone.utc).isoformat(), 'status': 'running',
             'thread_id': config['thread_id'], 'log': f'audit/runlogs/queue-{stamp}.log'}
    (AUDIT / 'scheduler_status.json').write_text(json.dumps(state, indent=2))
    # App owns this thread's writer. Queue into that owner instead of opening a second writer.
    cmd = ['/usr/bin/codex', 'queue', '--thread', config['thread_id'],
           '--message', prompt, '-C', str(REPO)]
    outcome = subprocess.run(cmd, text=True, cwd=REPO, env=env, capture_output=True, timeout=90)
    (logs / f'queue-{stamp}.log').write_text(outcome.stdout + outcome.stderr)
    state.update(status='queued' if outcome.returncode == 0 else 'queue_failed', returncode=outcome.returncode,
                 ended_at=datetime.now(timezone.utc).isoformat())
    (AUDIT / 'scheduler_status.json').write_text(json.dumps(state, indent=2))
    print(f'Audit continuation queue exit code {outcome.returncode}.')
    if outcome.returncode:
        raise SystemExit(outcome.returncode)


if __name__ == '__main__':
    main()

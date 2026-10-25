"""Check the existing pilot every 30 minutes; queue this thread only on stop.

This observer never launches generation, contacts the endpoint, scores, or changes
scientific artifacts. The independently reviewed supervisor owns those actions.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time


INTERVAL = 30 * 60
ACTIVE = {'generation_active', 'generation_frozen_scoring'}


def utc(timestamp=None):
    return datetime.fromtimestamp(time.time() if timestamp is None else timestamp,
                                  timezone.utc).isoformat()


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generation', type=Path, required=True)
    parser.add_argument('--thread', required=True)
    args = parser.parse_args()
    generation = args.generation.resolve()
    monitor = generation.parent / 'monitor_v2'
    lock = (monitor / 'scheduled_observer.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    receipt = monitor / 'scheduled_callback.json'
    if receipt.exists() and json.loads(receipt.read_text()).get('queued'):
        return
    repo = Path(__file__).resolve().parents[3]
    deadline = time.monotonic() + 24 * 3600
    attempts = 0
    previous_progress = None
    progress_at = time.monotonic()
    while True:
        try:
            status = json.loads((monitor / 'status.json').read_text())
        except (OSError, ValueError):
            status = {'state': 'monitor_status_unavailable'}
        responses = len(list(generation.rglob('response.json')))
        results = len(list(generation.rglob('result.json')))
        progress = (responses, results, status.get('state'), status.get('restarts'))
        if progress != previous_progress:
            previous_progress = progress
            progress_at = time.monotonic()
        reason = None
        if status.get('state') not in ACTIVE:
            reason = 'supervisor_terminal_or_unavailable'
        elif time.monotonic() - progress_at >= 2 * INTERVAL:
            reason = 'no_observed_progress_for_60_minutes'
        elif time.monotonic() >= deadline:
            reason = 'observer_24_hour_deadline'
        snapshot = {'pid': os.getpid(), 'interval_seconds': INTERVAL,
                    'checked_at_utc': utc(), 'next_check_at_utc': utc(time.time() + INTERVAL),
                    'responses': responses, 'complete_cases': results,
                    'supervisor': status, 'notification_reason': reason}
        write(monitor / 'scheduled_observer.json', snapshot)
        if reason:
            prompt = (
                'Scheduled v63 pilot check: ' + reason + '. Read ' + str(monitor) +
                '/status.json and scheduled_observer.json. Verify actual generation/scoring '
                'artifacts and report in Vietnamese. Do not start duplicate controllers, '
                'change frozen generator code, reset attempts, expand the cohort, or use '
                'another provider. If complete, audit/report five-arm scores, writer '
                'admission, witness/final realization, errors and actual usage; preserve '
                'the distinction between interface failure and concept efficacy. If '
                'incomplete, diagnose the exact stop; user authorizes fixing implementation '
                'failures autonomously in isolated reviewed successors, without changing '
                'frozen artifacts or treating failed gates as concept inefficacy. User requests sparse scheduled '
                'monitoring: no minute-by-minute polling. Keep endpoint secret. Update '
                'own reports/memory and commit/push own files per standing instructions.'
            )
            attempts += 1
            try:
                outcome = subprocess.run(
                    ['/usr/bin/codex', 'queue', '--thread', args.thread,
                     '--message', prompt, '-C', str(repo)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=45,
                )
                queued = outcome.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                queued = False
            write(receipt, {'queued': queued, 'attempt': attempts,
                            'at_utc': utc(), 'reason': reason})
            if queued or attempts >= 3:
                return
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()

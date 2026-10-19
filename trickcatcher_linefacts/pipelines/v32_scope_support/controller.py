"""Single detached GPU waiter + feasibility controller. Endpoint remains in environment."""
import datetime as dt
import fcntl
import json
import os
import sys
import time

from . import gate
from .common import D, write_json
from .diagnostic_client import Client


def now():
    return dt.datetime.now(dt.timezone.utc)


def main():
    root = gate.ROOT; root.mkdir(parents=True, exist_ok=True)
    with (root / 'wrapper.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 1
        status = {'state': 'waiting_for_gpu', 'pid': os.getpid(), 'scope': 'feasibility5 only; no comparison/benchmark',
                  'started_at': now().isoformat(), 'exit_code': None}
        write_json(root / 'status.json', status)
        try:
            gate.verify_preflight(); gate.freeze()
            if (root / 'run_frozen.json').exists():
                report = gate.report()
                failed = next((k for k, v in report['gates'].items() if v is False), None)
                status.update(state='gate_failed_' + failed if failed else 'feasibility_passed_review_pending',
                              exit_code=0, gates=report['gates'], costs=report['costs'], backend=report['backend'],
                              completed_resume_without_network=True)
                return 0
            earliest = dt.datetime.fromisoformat(D['not_before_utc'])
            deadline = max(now(), earliest) + dt.timedelta(seconds=D['wait_seconds'])
            ready = False
            while now() < deadline:
                if now() < earliest:
                    time.sleep(min(60, (earliest - now()).total_seconds())); continue
                try:
                    probe = Client(root / 'transport'); probe.close(); ready = True; error = None
                except Exception as exc:
                    error = type(exc).__name__
                with (root / 'wait_checks.jsonl').open('a') as stream:
                    stream.write(json.dumps({'at': now().isoformat(), 'ready': ready, 'error_type': error}) + '\n')
                if ready:
                    break
                time.sleep(min(D['wait_interval'], max(0, (deadline - now()).total_seconds())))
            if not ready:
                status.update(state='wait_timeout', exit_code=2)
            else:
                status.update(state='running', online_started_at=now().isoformat())
                write_json(root / 'status.json', status)
                sys.argv = ['gate', 'online', '--online']; gate.main()
                report = json.loads((root / 'report.json').read_text())
                failed = next((k for k, v in report['gates'].items() if v is False), None)
                status.update(state='gate_failed_' + failed if failed else 'feasibility_passed_review_pending',
                              exit_code=0, gates=report['gates'], costs=report['costs'], backend=report['backend'])
        except BaseException as exc:
            status.update(state='incomplete', error_type=type(exc).__name__, exit_code=1, costs=gate.costs())
            status['case_coverage'] = {uid: {stage: (root / folder / (uid + '.json')).exists()
                for stage, folder in (('A', 'prepared_cases'), ('B', 'hypothesis_cases'), ('C', 'generation'))}
                for uid in gate.fixtures.IDS}
        finally:
            status['finished_at'] = now().isoformat(); write_json(root / 'status.json', status)
        return status['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())

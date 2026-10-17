"""Detached wrapper; never persists endpoint/credentials or exception messages."""
import datetime as dt
import fcntl
import json
import os
import sys

from . import diagnostic
from .diagnostic_client import write_json


def main():
    root = diagnostic.ROOT
    root.mkdir(parents=True, exist_ok=True)
    # Distinct lock: diagnostic.main owns the inner single-run lock.
    with (root / 'wrapper.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('controller_already_running')
        status = {'state': 'running', 'pid': os.getpid(),
                  'scope': 'diagnostic16 only; no automatic benchmark',
                  'started_at': dt.datetime.now(dt.timezone.utc).isoformat()}
        write_json(root / 'status.json', status)
        sys.argv = ['diagnostic', 'online', '--online']
        try:
            diagnostic.main()
            status.update(state='complete_semantic_review_pending', exit_code=0)
            if (root / 'report.json').exists():
                report = json.loads((root / 'report.json').read_text())
                status.update(totals=report['totals'], costs=report['costs'])
        except BaseException as exc:
            status.update(state='incomplete', error_type=type(exc).__name__, exit_code=1)
        finally:
            status['finished_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
            write_json(root / 'status.json', status)
        return status['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())

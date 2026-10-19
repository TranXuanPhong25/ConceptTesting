"""Durable one-attempt isolated worker launch; interrupted executions never auto-retry."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess

from .common import digest, immutable, write_json
from .paths import CONFIG, worker_env


def run_once(script, job, folder, timeout=8):
    folder = Path(folder)
    jp, op, ledger = folder / 'job.json', folder / 'result.json', folder / 'attempt.json'
    staging = folder / 'worker-output.part'  # Worker never writes the authoritative cache.
    immutable(jp, job)
    identity = digest({'job': job, 'script': str(script), 'interpreter': CONFIG['V4_PYTHON']})
    attempt = json.loads(ledger.read_text()) if ledger.exists() else None
    if attempt is not None and attempt['identity'] != identity:
        raise ValueError('worker_attempt_identity_drift')
    if op.exists():
        data = op.read_bytes()
        if attempt and attempt.get('result_sha256') and hashlib.sha256(data).hexdigest() != attempt['result_sha256']:
            raise ValueError('worker_result_drift')
        try:
            result = json.loads(data)
        except (ValueError, UnicodeError):
            if attempt and attempt.get('result_sha256'):
                raise ValueError('worker_result_drift') from None
            result = {'status': 'unresolved', 'reason': 'partial_worker_result_not_retried', 'events': [],
                      'rows': [{'state': 'unknown', 'reason': 'partial_worker_result_not_retried'} for _ in job.get('rows', [])]}
            write_json(op, result)
            attempt = attempt or {'identity': identity, 'launched': None}
            attempt.update(state='partial_result_cached_unknown', resume_cached_unknown=True,
                           result_sha256=hashlib.sha256(op.read_bytes()).hexdigest())
            write_json(ledger, attempt)
            return result
        if attempt and not attempt.get('result_sha256'):
            attempt.update(state='recovered_result', result_sha256=hashlib.sha256(data).hexdigest())
            write_json(ledger, attempt)
        return result
    if attempt is not None:
        result = {'status': 'unresolved', 'reason': 'interrupted_worker_attempt_not_retried',
                  'events': [], 'rows': [{'state': 'unknown', 'reason': 'interrupted_worker_attempt_not_retried'}
                                        for _ in job.get('rows', [])]}
        write_json(op, result)
        attempt.update(resume_cached_unknown=True, result_sha256=hashlib.sha256(op.read_bytes()).hexdigest())
        write_json(ledger, attempt)
        return result
    attempt = {'identity': identity, 'state': 'reserved', 'launched': None}
    write_json(ledger, attempt)  # Reserve durably BEFORE spawn; crash consumes the attempt.
    process = None
    try:
        process = subprocess.Popen(['unshare', '-rn', CONFIG['V4_PYTHON'], '-I', '-B', str(script), str(jp), str(staging)],
                                   cwd=folder, env=worker_env(), stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        attempt.update(state='launched', launched=True, pid=process.pid)
        write_json(ledger, attempt)
        code = process.wait(timeout=timeout)
        if code != 0 or not staging.exists() or staging.stat().st_size > 8 * 1024 * 1024:
            raise RuntimeError('worker_failed')
        result = json.loads(staging.read_text())
        write_json(op, result)  # Atomic controller promotion after completed process/JSON validation.
        attempt.update(state='completed', exit_code=code)
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL); process.wait()
        result = {'status': 'unresolved', 'reason': 'isolated_worker_failed', 'events': [],
                  'rows': [{'state': 'unknown', 'reason': 'isolated_worker_failed'} for _ in job.get('rows', [])]}
        write_json(op, result)
        attempt.update(state='failed', launched=process is not None)
    attempt['result_sha256'] = hashlib.sha256(op.read_bytes()).hexdigest()
    write_json(ledger, attempt)
    return result

"""One authorized delayed launch; frozen experiment code is not modified."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path('/home/phong/dev/ConceptTester')
HERE = Path(__file__).resolve().parent
OUT = REPO / 'trickcatcher_linefacts/pipelines/vr12_expanded/out/humaneval/diagnostic'
PYTHON = REPO / 'trickcatcher_linefacts/handoffs/v85_20261029/.venv/bin/python'
MODULE = 'trickcatcher_linefacts.pipelines.vr12_expanded.diagnostic'


def event(stage, **fields):
    row = dict(time=datetime.now(timezone.utc).isoformat(), stage=stage, **fields)
    with (HERE / 'events.jsonl').open('a') as handle:
        handle.write(json.dumps(row) + '\n')
    print(json.dumps(row), flush=True)


def main():
    with (HERE / 'schedule.lock').open('a') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (HERE / 'LAUNCH_ATTEMPTED.json').exists():
            event('skip_already_attempted')
            return
        if (OUT / 'COMPLETE.json').exists():
            event('skip_experiment_complete')
            return
        with (OUT / 'RUN.lock').open('a') as run_lock:
            try:
                fcntl.flock(run_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                event('skip_active_controller_lock')
                return
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():
                continue
            try:
                args = (proc / 'cmdline').read_bytes().split(b'\0')
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue
            if MODULE.encode() in args and b'run' in args:
                event('skip_active_controller_process')
                return
        ledger = OUT / 'transport/attempts.jsonl'
        if ledger.exists() and ledger.read_text().strip():
            event('blocked_existing_completion_attempts_no_automatic_resume')
            return
        if not os.environ.get('CT_RETRIEVAL_BASE_URL'):
            event('blocked_missing_endpoint_environment')
            return
        env = {k: v for k, v in os.environ.items() if not k.startswith('LINEFACTS_')}
        env['PYTHONPATH'] = str(REPO)
        checked = subprocess.run([str(PYTHON), '-m', MODULE, 'check'], cwd=REPO, env=env)
        if checked.returncode:
            event('blocked_frozen_check', returncode=checked.returncode)
            return
        # Keep the original failed-preflight receipts; never reset/delete the run.
        backup = OUT / 'history/pre_schedule_20261030'
        backup.mkdir(parents=True, exist_ok=False)
        for name in ('LAUNCH.json', 'STATUS.json', 'controller.pid', 'runner.log'):
            if (OUT / name).exists():
                shutil.copy2(OUT / name, backup / name)
        with (HERE / 'LAUNCH_ATTEMPTED.json').open('x') as handle:
            json.dump(dict(time=datetime.now(timezone.utc).isoformat(),
                           policy='single_launch_zero_completion_retries'), handle)
        event('launch_frozen_vr12', tasks=11, arms=4, K=1, completion_cap=132)
        with (OUT / 'scheduled_runner_20261030.log').open('x') as log:
            result = subprocess.run([str(PYTHON), '-m', MODULE, 'run'], cwd=REPO,
                                    env=env, stdout=log, stderr=subprocess.STDOUT)
        event('controller_exited', returncode=result.returncode,
              complete=(OUT / 'COMPLETE.json').exists())


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        event('wrapper_blocked', error_type=type(exc).__name__)
        sys.exit(1)

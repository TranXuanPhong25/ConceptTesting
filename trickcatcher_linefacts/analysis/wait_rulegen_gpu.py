"""Wait for the user-authorized GPU, then run unchanged v19; no endpoint persistence."""
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.pipelines.v19_rulegen import behavior_experiment as experiment
from trickcatcher_linefacts.pipelines.v19_rulegen.llm_client import NoRedirect, atomic_json


def main():
    directory = REPO / 'trickcatcher_linefacts/out/runlogs_v19_rulegen'
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'waiter.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('GPU waiter already running')
        experiment.verify()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        status = dict(state='waiting_for_gpu', pid=os.getpid(), attempts=0,
                      started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                      interval_seconds=60, maximum_wait_seconds=7200)
        deadline = time.monotonic() + 7200
        while time.monotonic() < deadline:
            status['attempts'] += 1
            status['checked_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
            try:
                headers = {'ngrok-skip-browser-warning': '1'}
                if os.environ.get('QWEN_API_KEY'):
                    headers['Authorization'] = 'Bearer ' + os.environ['QWEN_API_KEY']
                request = urllib.request.Request(os.environ['QWEN_BASE_URL'].rstrip('/') + '/models', headers=headers)
                with opener.open(request, timeout=10) as response:
                    models = json.loads(response.read(100000))
                ready = any(row.get('id') == 'qwen2.5-coder-7b-instruct' for row in models.get('data', []))
                status['last_check'] = 'pinned_model_ready' if ready else 'pinned_model_unavailable'
            except Exception as exc:
                ready = False
                status['last_check'] = type(exc).__name__
                if hasattr(exc, 'code'):
                    status['http_status'] = exc.code
            if ready:
                experiment.verify()
                status['state'] = 'controller_started'
                atomic_json(directory / 'waiter_status.json', status)
                result = subprocess.run([sys.executable, '-B', str(REPO / 'trickcatcher_linefacts/analysis/run_rulegen.py')],
                                        cwd=REPO, stdin=subprocess.DEVNULL, check=False)
                status.update(state='controller_returned', controller_exit_code=result.returncode)
                atomic_json(directory / 'waiter_status.json', status)
                return
            atomic_json(directory / 'waiter_status.json', status)
            time.sleep(60)
        status['state'] = 'gpu_wait_timeout'
        atomic_json(directory / 'waiter_status.json', status)
        message = ('v19_rulegen GPU waiter timed out after two hours; no live pinned model was observed. '
                   'Read trickcatcher_linefacts/out/runlogs_v19_rulegen/waiter_status.json. '
                   'Report actual status; preserve frozen treatment and request current GPU endpoint. No paid fallback.')
        subprocess.run(['/usr/bin/codex', 'queue', '--thread', '01a1387b-2603-7221-8fd0-b314052b1085',
                        '--message', message, '-C', str(REPO)], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60, check=False)


if __name__ == '__main__':
    main()

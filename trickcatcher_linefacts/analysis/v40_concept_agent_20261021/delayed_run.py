"""User-authorized delayed launch of unchanged v40. Endpoint stays in process env.

This uses the existing runnable diagnostic directly. Callback uses `codex queue`
instead of opening a second CLI writer on the existing conversation.
"""
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.pipelines.v40_concept_agent import d1


def write(path, value):
    d1.write_json(path, value)


def main():
    root = d1.ROOT
    record_path = root / 'delayed_launch.json'
    with (root / 'delayed_controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = d1.read(record_path)
        if state['state'] != 'scheduled':
            raise RuntimeError('not_a_fresh_scheduled_launch')
        state.update(controller_pid=os.getpid(), state='waiting_not_before')
        write(record_path, state)
        try:
            while time.time() < state['not_before_unix']:
                time.sleep(min(30, state['not_before_unix'] - time.time()))
            spec = importlib.util.spec_from_file_location('owned_quota_guard', d1.QUOTA)
            guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
            while True:
                snapshot = guard.quota()
                state['quota'] = snapshot
                if snapshot['should_stop']:
                    reset = snapshot.get('reset_unix')
                    if type(reset) not in (int, float):
                        raise RuntimeError('quota_reset_unknown')
                    wake = max(time.time() + 60, reset + 120)
                    state.update(state='waiting_quota_reset', next_quota_check_unix=wake)
                    write(record_path, state)
                    while time.time() < wake:
                        time.sleep(min(30, wake - time.time()))
                    continue
                d1.verify(root)
                if (root / 'generation_frozen.json').exists():
                    state['state'] = 'already_complete_no_duplicate'
                    break
                state.update(state='launching', launched_at_utc=datetime.now(timezone.utc).isoformat())
                write(record_path, state)
                command = [sys.executable, '-B', '-m', 'trickcatcher_linefacts.pipelines.v40_concept_agent.d1', 'run', '--online']
                done = subprocess.run(command, cwd=REPO, stdin=subprocess.DEVNULL)
                state.update(state='controller_exited', returncode=done.returncode,
                             diagnostic_status=d1.read(root / 'status.json'))
                if state['diagnostic_status'].get('reason') == 'quota_at_or_below15':
                    continue  # Only this explicit safe checkpoint may resume; never transport/unknown attempts.
                break
        except Exception as exc:
            state.update(state='schedule_stopped', error_type=type(exc).__name__)
        write(record_path, state)
        prompt = ('Owned user-authorized v40 Astra D1 delayed Qwen32B diagnostic has finished/stopped. '
                  'Read status, delayed_launch and frozen/prepared/transport/artifacts under '
                  '/home/phong/dev/ConceptTester/trickcatcher_linefacts/out/pipelines/v40_concept_agent/humaneval/d1. '
                  'Do not duplicate launch, repair frozen treatment/output, reset attempts or expand benchmark/paid/training. '
                  'Check Codex5h quota; stop at15%. If complete, independently review actual all8episodes/3arms '
                  'including failures/abstentions, predictions/tool evidence/selective revision and controls, run saved-data '
                  'post-freeze scoring, report actual costs/unknowns/worker calls, update own analysis/RESULTS/memory '
                  'and commit/push own files main. If incomplete report exact terminal cause and all not-attempted slots. '
                  'Endpoint secrecy and other sessions files preserved. Reply Vietnamese.')
        callback = subprocess.run(['codex', 'queue', '--thread', state['thread_id'], '--message', prompt],
                                  cwd=REPO, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        state['callback'] = {'method': 'codex_queue_existing_thread', 'returncode': callback.returncode}
        write(record_path, state)
        print(json.dumps({'state': state['state'], 'callback': state['callback']}), flush=True)


if __name__ == '__main__': main()

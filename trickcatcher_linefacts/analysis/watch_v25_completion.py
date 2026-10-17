"""Notify this same Codex thread when the owned detached diagnostic stops. No endpoints."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / 'trickcatcher_linefacts/out/pipelines/v25_interface_gate/humaneval/feasibility5'


def main():
    from sys import path
    path.insert(0, str(REPO))
    from trickcatcher_linefacts.pipelines.v25_interface_gate.diagnostic_client import write_json
    with (ROOT / 'watcher.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        if (ROOT / 'notification.json').exists() and json.loads((ROOT / 'notification.json').read_text()).get('queued'):
            return
        while True:
            if not (ROOT / 'status.json').exists():
                time.sleep(1)
                continue
            status = json.loads((ROOT / 'status.json').read_text())
            if status['state'] not in ('waiting_for_gpu', 'running'):
                break
            stat = Path('/proc') / str(status['pid']) / 'stat'
            if not stat.exists() or stat.read_text().rsplit(')', 1)[-1].strip().startswith('Z '):
                break
            time.sleep(30)
        prompt = (
            'Owned user-authorized v25_interface_gate feasibility5 finished/stopped. Read '
            +str(ROOT)+'/status.json and report/artifacts. Verify frozen source, prepared data '
            'and run_frozen.json, raw Qwen origin/usage/cumulative attempts; do not relaunch or '
            'edit frozen source/prompts/serialization. Report A/B/C gates, failed/blocked/NA '
            'slots for all5 seen fixtures, semantic calibration coverage and ambiguity, code '
            'envelopes and raw-text control provenance. Capability echo and chosen mode are '
            'separate from task performance. Whole single-fence decoding is prospectively '
            'registered only for v25; never recover v24 historical outputs or swap/fill fields. '
            'Independently review actual model metadata/code/behavior/hypotheses/triggers/inputs '
            'with clean-context reviewer if needed. Gate failure stops dependent phases; no '
            'automatic full comparison, benchmark, real20, held-out, paid fallback or new '
            'prompt adaptation. If complete phase C, report valid discriminator/contrast/'
            'abstention and novel inputs/tasks outside ENTIRE24+base witness pool, not just '
            'shown six. Finite authored calibration is not reference-free semantic proof. '
            'Preserve all rejected raw artifacts, source/worker guards, failures/costs, '
            'no automatic retries of unknown worker attempts. Update own analysis/RESULTS/'
            'memory, commit/push own files to main, preserve others and endpoint secrecy. '
            'Reply in Vietnamese. If callback already handled, reverify and do not duplicate work.')
        for attempt in range(3):
            try:
                result = subprocess.run(['/usr/bin/codex', 'queue', '--thread', os.environ['CODEX_THREAD_ID'],
                                         '--message', prompt, '-C', str(REPO)],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
                ok = result.returncode == 0
            except Exception:
                ok = False
            write_json(ROOT / 'notification.json', {'queued': ok, 'attempt': attempt + 1})
            if ok:
                return
            time.sleep(30)


if __name__ == '__main__':
    main()

"""Notify this same Codex thread when the owned detached diagnostic stops. No endpoints."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / 'trickcatcher_linefacts/out/pipelines/v23_concepthyp/humaneval/concept_hypothesis_diagnostic'


def main():
    from sys import path
    path.insert(0, str(REPO))
    from trickcatcher_linefacts.pipelines.v23_concepthyp.diagnostic_client import write_json
    with (ROOT / 'watcher.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        if (ROOT / 'notification.json').exists() and json.loads((ROOT / 'notification.json').read_text()).get('queued'):
            return
        while True:
            status = json.loads((ROOT / 'status.json').read_text())
            if status['state'] != 'running':
                break
            stat = Path('/proc') / str(status['pid']) / 'stat'
            if not stat.exists() or stat.read_text().rsplit(')', 1)[-1].strip().startswith('Z '):
                break
            time.sleep(30)
        prompt = (
            'Owned user-authorized v23_concepthyp diagnostic16 has finished or stopped. '
            'Read status.json and artifacts under ' + str(ROOT) + '. Verify frozen source and '
            'generation; do not edit treatment/schema/prompts or duplicate launch. If complete, '
            'read actual Qwen concepts/behaviors/hypotheses/tests, independently review semantic '
            'correctness and practical discriminators, report all16 including failures/abstentions, '
            'compare concept_chain/direct_chain/hyp_only and inspect correct/ambiguous/masked cases. '
            'Report actual tokens/requests, assert vs input yield and false alarms. Preserve raw '
            'Qwen artifact origin; Luna probe is separate and null. If incomplete, diagnose exact '
            'terminal transport/protocol/counterexample cause and report without repairing or '
            'resetting attempts. No automatic benchmark/real20/held-out/paid calls. Update own '
            'RESULTS/analysis/memory and commit/push own changes to main per standing permission; '
            'preserve other sessions files and endpoint secrecy. Give Vietnamese result to user.')
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

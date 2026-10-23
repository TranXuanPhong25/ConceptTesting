"""One detached launch of frozen v50 on the explicitly supplied temporary endpoint.

No endpoint is stored here, no retries, no mutation of frozen treatment or outcomes.
Terminal callback queues this same user thread for saved-data review.
"""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.pipelines.v50_binding_revision import revision as app
from trickcatcher_linefacts.pipelines.v50_binding_revision.flow_common import immutable, write_json

HERE = Path(__file__).resolve().parent
RUNTIME = HERE/'temporary_launch'


def main():
    RUNTIME.mkdir(exist_ok=True)
    with (RUNTIME/'launcher.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        registration = app.read(RUNTIME/'registration.json')
        if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != registration['launcher_sha256']:
            raise SystemExit('launcher_source_drift')
        if (RUNTIME/'launch_state.json').exists() or (app.ROOT/'status.json').exists():
            raise SystemExit('launch_already_consumed')
        app.verify(full=True)
        app.approval_matches(app.ROOT, 'launch')
        state = {'state': 'starting', 'pid': os.getpid(), 'started_utc': datetime.now(timezone.utc).isoformat()}
        write_json(RUNTIME/'launch_state.json', state)
        try:
            result = subprocess.run([sys.executable, '-B', '-m',
                       'trickcatcher_linefacts.pipelines.v50_binding_revision.revision', 'run'],
                       cwd=REPO, stdin=subprocess.DEVNULL)
            state.update(state='child_exited', child_exit_code=result.returncode,
                         diagnostic_status=app.read(app.ROOT/'status.json') if (app.ROOT/'status.json').exists() else None)
            app.verify(full=True)
            state['integrity_after_child'] = 'PASS'
        except Exception as exc:
            state.update(state='launcher_stopped', error_type=type(exc).__name__)
        state['ended_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(RUNTIME/'launch_state.json', state)
        immutable(RUNTIME/'terminal_inventory.json', app.files(app.ROOT))
        message = (
            'Owned explicitly user-authorized v50 binding-revision diagnostic finished/stopped on the temporary endpoint. '
            'Read status, slots, checkpoints, launch approval, freeze and artifacts under '
            '/home/phong/dev/ConceptTester/trickcatcher_linefacts/out/pipelines/v50_binding_revision/humaneval/revision8 '
            'and analysis/v50_binding_revision_20261023, including temporary_launch. '
            'Check Codex5h quota>15; stop<=15. No duplicate/retry/reset/repair/new calls. '
            'Verify frozen64sources/eightpools/deps/evaluator rubric, old v43/v40 and new generation/terminal inventories. '
            'If complete independently review ALL8initial and16paired raw/tool finals including partial-invalid, unknown, '
            'abstention and over-cap slots with clean-context reviewer under EVALUATION.md. Report bindings/label/quote/argument '
            'quality, required-facet coverage, semantic retention/correction/addition/loss, judgments and evidence; E7 correct '
            'and E8 ambiguous; same-evidence parity; prereg >=2 genuine tool-only wins/0 opposite losses and controls. '
            'Derived comparison feedback conditional on revision, no causal revision-effect or concept discovery claim. '
            'No new PUTs:78saved biased observations; dynamic search/runtime tools were synthetic CPU-only, excluded from model treatment. '
            'Report actual completions/known tokens/unknowns/metadata and all24slot statuses. http_sent:false on over-cap '
            'means completion not sent, tokenizer may have been sent; syntactic removed transitions are not semantic losses. '
            'If incomplete report exact terminal cause without repair. Old waiting launcher was disabled for this user-requested '
            'temporary endpoint, never restart it. No benchmark/training/paid fallback/new calls. Update own RESULTS/analysis/memory '
            'and commit/push own files main; preserve other sessions and endpoint secrecy. Reply Vietnamese. '
            'If callback already handled, reverify only.')
        result = subprocess.run(['codex', 'queue', '--thread', registration['thread_id'], '--message', message],
                                cwd=REPO, capture_output=True, text=True, timeout=30)
        write_json(RUNTIME/'callback.json', {'method': 'codex_queue', 'returncode': result.returncode})


if __name__ == '__main__':
    main()

#!/usr/bin/env bash
# Run only after the user's separate go-ahead. No scheduler or background launch.
set -euo pipefail
set +x
cd "$(dirname "$0")/../../.."
if [[ "${1:-}" != --launch || $# != 3 || "${2:-}" != --model ]]; then
  echo 'Prepared only. After approval: bash trickcatcher_linefacts/pipelines/v76_ossmodel/run_openrouter.sh --launch' >&2
  exit 2
fi
case "${3:-}" in
  gpt-oss-120b) MODEL_ID=openai/gpt-oss-120b ;;
  deepseek-v4-flash) MODEL_ID=deepseek/deepseek-v4-flash-0731 ;;
  *) echo 'Unknown registered model' >&2; exit 2 ;;
esac
export LINEFACTS_MODEL="$3"
source scripts/openrouter_env.sh >/dev/null 2>&1
export OPENROUTER_MODEL="$MODEL_ID" OPENROUTER_MAX_USD=3
export PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1
PY="${V76_PYTHON:-/tmp/concepttester-v74-venv/bin/python}"
# This maintenance code lives in a shell script, outside fingerprinted Python.
# Logs are archived outside the pipeline. Never modify any pipeline .py mid-run.
"$PY" -B - <<'PY'
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import shutil
from trickcatcher_linefacts.pipelines.v76_ossmodel.run_v76 import V76Run
from trickcatcher_linefacts.pipelines.v76_ossmodel.flow_client import write_json
run = V76Run()
run.root.mkdir(parents=True, exist_ok=True)
with (run.root / '.run.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if not (run.root / 'generation_frozen.json').exists():
        archive = run.root.parent / 'resume_archives' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        for path in (run.root / 'transport/calls').rglob('attempts.json'):
            attempts = json.loads(path.read_text())
            if any(a.get('state') == 'workspace_403' for a in attempts):
                target = archive / path.relative_to(run.root)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                # Keep charged incomplete attempts in the inherited retry cap.
                write_json(path, [a for a in attempts if a.get('state') != 'workspace_403'])
        for case in run.cases:
            for arm in ('plain', 'fault-template', 'template-placebo'):
                base = run.root / 'cases' / case['case_id'] / 'arms' / arm
                ledger = base / 'tools/ledger.json'
                if not (base / 'result.json').exists() and ledger.exists():
                    target = archive / ledger.relative_to(run.root)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(ledger), target)
PY
exec "$PY" -B -m trickcatcher_linefacts.pipelines.v76_ossmodel.run_v76 --launch --model "$3"

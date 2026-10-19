#!/usr/bin/env bash
# v31 launcher: tool stage, generation (OpenRouter), freeze, score. Resumable.
# Usage (repo root): bash trickcatcher_linefacts/pipelines/v31_faulttemplate/run_openrouter.sh [vibepass_half (default, MVP)|vibepass|pilot20]
set -euo pipefail
cd "$(dirname "$0")/../../.."
source scripts/openrouter_env.sh >/dev/null
export PYTHONPATH="$PWD"
PY=$(python3 -c "import json;print(json.load(open('trickcatcher_linefacts/pipelines/v31_faulttemplate/config.json'))['V4_PYTHON'])")
M=trickcatcher_linefacts.pipelines.v31_faulttemplate.ft_run
for c in "${1:-vibepass_half}"; do
  "$PY" -m $M tools --cohort "$c"
  "$PY" -m $M generate --cohort "$c"
  "$PY" -m $M score --cohort "$c"
done
echo CHAIN_DONE

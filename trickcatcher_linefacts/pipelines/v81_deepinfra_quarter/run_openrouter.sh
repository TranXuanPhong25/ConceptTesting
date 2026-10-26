#!/usr/bin/env bash
set -euo pipefail
set +x
if [[ "${1:-}" != --launch || $# != 1 ]]; then
  echo 'Usage: run_openrouter.sh --launch (fixed DeepInfra quarter, two arms K1)' >&2
  exit 2
fi
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
source scripts/research_env.sh >/dev/null 2>&1
source scripts/openrouter_env.sh >/dev/null 2>&1
export LINEFACTS_MODEL=deepseek-v4-flash
export OPENROUTER_MODEL=deepseek/deepseek-v4-flash-0731
export OPENROUTER_MAX_USD=4.20
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD"
exec /tmp/concepttester-v74-venv/bin/python -B -u -m trickcatcher_linefacts.pipelines.v81_deepinfra_quarter.run_v81 launch

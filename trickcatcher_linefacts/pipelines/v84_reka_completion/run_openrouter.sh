#!/usr/bin/env bash
set -euo pipefail
set +x
if [[ "${1:-}" != --launch || $# != 1 ]]; then
  echo 'Usage: run_openrouter.sh --launch (V84 two-task completion addendum, cap $0.50)' >&2
  exit 2
fi
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
source scripts/research_env.sh >/dev/null 2>&1
source scripts/openrouter_env.sh >/dev/null 2>&1
export LINEFACTS_MODEL=deepseek-v4-flash
export OPENROUTER_MODEL=deepseek/deepseek-v4-flash-0731
export OPENROUTER_MAX_USD=0.50
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD"
HOST_BIN=/tmp/concepttester-v74-venv/bin/python
"$HOST_BIN" -c 'import openai, tiktoken' >/dev/null
exec "$HOST_BIN" -B -u -m trickcatcher_linefacts.pipelines.v84_reka_completion.complete launch

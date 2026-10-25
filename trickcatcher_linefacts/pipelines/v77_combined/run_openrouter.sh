#!/usr/bin/env bash
set -euo pipefail
set +x
if [[ "${1:-}" != --launch || $# != 5 || "${2:-}" != --model || "${4:-}" != --dataset ]]; then
  echo 'Preparation only. After approval: run_openrouter.sh --launch --model MODEL --dataset DATASET' >&2
  exit 2
fi
case "$3" in
  gpt-oss-120b) MODEL_ID=openai/gpt-oss-120b ;;
  deepseek-v4-flash) MODEL_ID=deepseek/deepseek-v4-flash-0731 ;;
  *) echo 'Unknown registered model' >&2; exit 2 ;;
esac
case "$5" in humaneval|vibepass_half) ;; *) exit 2 ;; esac
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
export LINEFACTS_MODEL="$3"
source scripts/openrouter_env.sh >/dev/null 2>&1
export OPENROUTER_MODEL="$MODEL_ID"
# The Python harness clamps the inherited key cap to its dataset share.
unset OPENROUTER_MAX_USD
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD"
exec "${V77_PYTHON:-/tmp/concepttester-v74-venv/bin/python}" -B -m trickcatcher_linefacts.pipelines.v77_combined.run_v77 --launch --model "$3" --dataset "$5"

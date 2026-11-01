#!/usr/bin/env bash
set +x
set -euo pipefail
task_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$task_repo_root"
source scripts/research_env.sh >/dev/null 2>&1
# This file lives outside the repo; never print its contents.
source "${FINAL_ENDPOINT_ENV_FILE:-/tmp/concepttester-final-qwen.env}"
: "${FINAL_BASE_URL:?Set endpoint in FINAL_ENDPOINT_ENV_FILE}"
: "${FINAL_MODEL:?Set model in FINAL_ENDPOINT_ENV_FILE}"
task_run_out="${FINAL_RUN_OUT:-final/out/concept_reference_v1}"
mkdir -p "$task_run_out"
setsid nohup final/.venv/bin/python -m final.experiments.concept_reference_v1.run \
  --out "$task_run_out" "$@" >"$task_run_out/run.log" 2>&1 < /dev/null &
task_run_pid=$!
printf '%s\n' "$task_run_pid" > "$task_run_out/controller.pid"
printf 'Started controller PID %s; status: %s/status.json\n' "$task_run_pid" "$task_run_out"

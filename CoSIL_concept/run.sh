#!/usr/bin/env bash
# CoSIL concept/placebo experiment driver. Every step is idempotent and resumable: rerun to continue.
#   ./run.sh setup                          clone CoSIL @ pinned SHA, .venv, deps, selftest
#   ./run.sh data                           download pinned datasets -> data/
#   ./run.sh structures [ds|all] [--limit N] [--jobs N]   CoSIL repo structures + patch ground truth
#   ./run.sh lint [ds] [--jobs N]          ruff warnings per function (the ide arm's tags), needs structures
#   ./run.sh smoke                          3 instances x 4 arms end to end (+ eval, verify)
#   ./run.sh run <files|stock|concept|placebo|ide|all> [ds] [--limit N] [--ids FILE]
#                                           all = files stage, lint, then the four arms in parallel
#   ./run.sh eval [ds]                      authors' Acc@1/3/5, MAP, MRR per arm -> out/<ds>/
#   ./run.sh analyze [ds]                   McNemar / Wilcoxon / per-concept + offline tag check
# ds: swebench_live (default, post-cutoff) | locbench | swebench_lite
# env: COSIL_THREADS (default 4), COSIL_MAX_USD (per process, default unlimited), COSIL_MODEL
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(cd .. && pwd)
PY=.venv/bin/python
export PYTHONUTF8=1 HF_HOME="$PWD/cache/hf" HF_HUB_DISABLE_PROGRESS_BARS=1 TIKTOKEN_CACHE_DIR="$PWD/cache/tiktoken"

vertex() {  # load project/location without printing them; LiteLLM reads VERTEXAI_*; credentials come from ADC
  if [ -z "${VERTEXAI_PROJECT:-${VERTEX_PROJECT:-}}" ] && [ -f "$ROOT/scripts/vertex_env.sh" ]; then
    # shellcheck disable=SC1091
    source "$ROOT/scripts/vertex_env.sh" >/dev/null
  fi
  export VERTEXAI_PROJECT="${VERTEXAI_PROJECT:-${VERTEX_PROJECT:?set VERTEX_PROJECT or source scripts/vertex_env.sh}}"
  export VERTEXAI_LOCATION="${VERTEXAI_LOCATION:-${VERTEX_LOCATION:-global}}"
  local adc="${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/application_default_credentials.json}"
  [ -f "$adc" ] || { echo "no ADC credentials at $adc (gcloud auth application-default login)" >&2; exit 1; }
}

ds_arg() { case "${1:-}" in swebench_live|locbench|swebench_lite) echo "$1";; *) echo swebench_live;; esac; }

cmd=${1:-}; shift || true
case "$cmd" in
  setup) ./setup.sh ;;
  data) $PY prepare.py data ;;
  lint) ds=$(ds_arg "${1:-}"); [ "${1:-}" = "$ds" ] && shift; $PY prepare.py lint "$ds" "$@" ;;
  structures)
    ds=${1:-swebench_live}; [ $# -gt 0 ] && shift
    if [ "$ds" = all ]; then for d in swebench_live locbench swebench_lite; do $PY prepare.py structures "$d" "$@"; done
    else $PY prepare.py structures "$ds" "$@"; fi ;;
  run)
    arm=${1:?arm: files|stock|concept|placebo|all}; shift
    ds=$(ds_arg "${1:-}"); [ "${1:-}" = "$ds" ] && shift
    vertex
    case "$arm" in
      files) $PY cosil_concept.py files "$ds" "$@" ;;
      stock|concept|placebo) $PY cosil_concept.py funcs "$arm" "$ds" "$@" ;;
      ide) $PY prepare.py lint "$ds" "$@" && $PY cosil_concept.py funcs ide "$ds" "$@" ;;
      all)
        $PY cosil_concept.py files "$ds" "$@"
        $PY prepare.py lint "$ds" "$@"
        mkdir -p "work/$ds"
        for a in stock concept placebo ide; do
          $PY cosil_concept.py funcs "$a" "$ds" "$@" > "work/$ds/run_$a.log" 2>&1 &
        done
        echo "[run] arms running in parallel; progress: tail -f work/$ds/run_{stock,concept,placebo}.log"
        wait
        tail -n 1 "work/$ds"/run_*.log ;;
      *) echo "unknown arm $arm" >&2; exit 2 ;;
    esac ;;
  smoke)
    ids=data/smoke_ids.txt
    $PY prepare.py structures swebench_live --ids $ids --jobs 3
    $PY prepare.py lint swebench_live --ids $ids --jobs 3
    vertex
    $PY cosil_concept.py files swebench_live --ids $ids --threads 3
    for a in stock concept placebo ide; do $PY cosil_concept.py funcs "$a" swebench_live --ids $ids --threads 3; done
    $PY cosil_concept.py verify swebench_live --ids $ids | tee out/swebench_live/verify_smoke.txt
    $PY analyze.py eval swebench_live --ids $ids
    $PY analyze.py stats swebench_live ;;
  eval) $PY analyze.py eval "$(ds_arg "${1:-}")" ;;
  analyze)
    ds=$(ds_arg "${1:-}")
    $PY analyze.py stats "$ds"
    $PY check_tags.py "$ds" | tee "out/$ds/check_tags.txt" ;;
  *) sed -n '2,13p' "$0"; exit 2 ;;
esac

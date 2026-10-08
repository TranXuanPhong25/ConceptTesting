#!/usr/bin/env bash
# CoverUp + concepts experiment driver. Every step is idempotent and resumable: rerun to continue.
#   ./run.sh setup                       vendor CoverUp + benchmark sources @ pinned SHAs, .venv, deps, selftest
#   ./run.sh bench                       import-check every subset module, record versions -> out/bench.json
#   ./run.sh smoke                       SMOKE_PKGS (default: codetiming sty) x 5 arms x seed 1, mutate, analyze
#   ./run.sh run <arm|all> [--seed K] [--pkgs a,b]   one CoverUp pass per package (all = the 5 arms in parallel)
#   ./run.sh mutate <arm|all> [--seed K] [--pkgs a,b]  mutmut on the generated tests (seed omitted = every seed)
#   ./run.sh analyze                     coverage, mutation score, cost, concept-site coverage, Wilcoxon -> out/
# arms: coverup concept concept_reason placebo_reason ide
# env: CU_RUN (default main; smoke uses smoke_$(uname -m)), CU_MAX_USD (default 40, all arms together), CU_CONCURRENCY (default 16), CU_MODEL, MUTMUT_JOBS
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(cd .. && pwd)
PY=.venv/bin/python
ARMS="coverup concept concept_reason placebo_reason ide"
export CU_RUN=${CU_RUN:-main}
LOGS=work/$CU_RUN/logs
export PYTHONUTF8=1 TIKTOKEN_CACHE_DIR="$PWD/cache/tiktoken"

vertex() {  # project/location without printing them; LiteLLM reads VERTEXAI_*; credentials come from ADC
  if [ -z "${VERTEXAI_PROJECT:-${VERTEX_PROJECT:-}}" ] && [ -f "$ROOT/scripts/vertex_env.sh" ]; then
    # shellcheck disable=SC1091
    source "$ROOT/scripts/vertex_env.sh" >/dev/null
  fi
  export VERTEXAI_PROJECT="${VERTEXAI_PROJECT:-${VERTEX_PROJECT:?set VERTEX_PROJECT or source scripts/vertex_env.sh}}"
  export VERTEXAI_LOCATION="${VERTEXAI_LOCATION:-${VERTEX_LOCATION:-global}}"
}

opts() {  # --seed K --pkgs a,b -> SEED PKGS
  SEED=1; PKGS=$(cut -d, -f2 data/subset.csv | cut -d. -f1 | uniq | tr '\n' ' ')
  while [ $# -gt 0 ]; do case "$1" in
    --seed) SEED=$2; shift 2 ;;
    --pkgs) PKGS=$(echo "$2" | tr , ' '); shift 2 ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac; done
}

run_arm() {  # arm: every package, sequentially; stops on budget (rc 3)
  local arm=$1 rc=0
  mkdir -p "$LOGS"
  for p in $PKGS; do
    echo "[run] $arm s$SEED $p $(date +%H:%M:%S)"
    $PY cu_concept.py gen "$arm" "$p" --seed "$SEED" >> "$LOGS/$arm.s$SEED.$p.log" 2>&1 || rc=$?
    [ $rc -eq 3 ] && { echo "[run] budget cap reached; stopping $arm"; return 3; }
    [ $rc -ne 0 ] && echo "[run] $arm s$SEED $p failed rc=$rc (see $LOGS/$arm.s$SEED.$p.log); rerun resumes"
    rc=0
  done
  tail -qn 1 "$LOGS/$arm.s$SEED".*.log
}

cmd=${1:-}; shift || true
case "$cmd" in
  setup) ./setup.sh ;;
  bench) $PY evaluate.py bench ;;
  run)
    arm=${1:?arm: $ARMS | all}; shift; opts "$@"; vertex
    if [ "$arm" = all ]; then
      mkdir -p "$LOGS"
      for a in $ARMS; do run_arm "$a" > "$LOGS/run_$a.s$SEED.log" 2>&1 & done
      echo "[run] 5 arms in parallel; tail -f $LOGS/run_*.s$SEED.log"; wait
    else run_arm "$arm"; fi ;;
  mutate)
    arm=${1:?arm: $ARMS | all}; shift
    [ "$arm" = all ] && arm=$(echo $ARMS | tr ' ' ,)
    $PY evaluate.py mutate "$arm" "$@" ;;
  analyze) $PY evaluate.py analyze ;;
  smoke)
    export CU_RUN=smoke_$(uname -m); LOGS=work/$CU_RUN/logs
    opts --pkgs "$(echo "${SMOKE_PKGS:-codetiming sty}" | tr ' ' ,)"; vertex
    for a in $ARMS; do run_arm "$a"; done
    $PY evaluate.py mutate "$(echo $ARMS | tr ' ' ,)" --seed 1 --pkgs "$(echo $PKGS | tr ' ' ,)"
    $PY evaluate.py analyze ;;
  *) sed -n '2,10p' "$0"; exit 2 ;;
esac

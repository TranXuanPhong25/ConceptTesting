#!/usr/bin/env bash
# m10 driver. usage (from anywhere): bash m10_fix_first/run.sh <checkout|smoke|phaseA|analyzeA|phaseB|analyzeB> [arg]
#   checkout [bug ...]  sequential Defects4J checkouts (buggy + fixed) of the 60 bugs into the d4jproj volume
#   smoke               idx 3 33 53 (Cli_32, Lang_20, Lang_40) through Phase A and a Phase B evaluation of A2
#   phaseA              env -> gen A1 A1r A2 A3 -> fix A0 A1 A1r A2 A3 -> cost
#   analyzeA            out/analysisA.txt, out/best_arm.txt
#   phaseB [arm]        docstrings -> test generation -> evaluation of m10_<arm> (default: out/best_arm.txt)
#   analyzeB [arm]      out/analysisB_<arm>.txt
# JOBS=N (default 4): parallel compile/run jobs (each with its own scratch copy) and parallel LLM calls.
# Every stage is idempotent and resumable: LLM calls, test runs and evaluations are cached; rerun a stage after a crash.
# Containers run one at a time (never two evaluations at once).
set -euo pipefail
cd "$(dirname "$0")/.."
D=m10_fix_first
JOBS=${JOBS:-4}
stage=${1:?usage: run.sh checkout|smoke|phaseA|analyzeA|phaseB|analyzeB}
shift
NEW="A1 A1r A2 A3"
SMOKE_BUGS="Cli_32 Lang_20 Lang_40"
DOC=Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m10_
log() { echo "[$(date '+%F %T')] m10 $*"; }
in_box() { bash $D/dock10.sh python3 -W ignore $D/m10.py "$@"; }        # sandbox: no credentials, no network
with_llm() { bash run/dock.sh -- python3 -W ignore $D/m10.py "$@"; }     # credentials, runs no LLM-written code
tests() {  # $1 = FILE_POST_FIX, $2 = number of records: upstream test generation, skipped when complete
  local f=data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_$1_with_completion.jsonl
  if [ -f "$f" ] && [ "$(wc -l < "$f")" -ge "$2" ]; then log "tests for $1 already generated"; return; fi
  log "test generation $1"
  env -u THINKING_BUDGET -u GEN_MODEL DOC_FILE=$DOC${1#m10_}.jsonl WITH_CODE=0 FILE_POST_FIX=$1 bash run/dock.sh gen_env
}
evaluate() {  # $1 = FILE_POST_FIX; resumable, NO_ADC=1 inside
  log "evaluation $1"
  python3 $D/eval_parts.py "$1"
  python3 run/summarize.py "$(python3 -c "import sys; sys.path.insert(0, '$D'); from eval_parts import latest_log; print(latest_log('$1'))")"
}

python3 $D/m10.py install
case $stage in
checkout)
  log "checkout (sequential)"; NO_ADC=1 bash run/dock.sh -- python3 $D/m10.py checkout "$@" ;;
smoke)
  log "smoke: checkout"; NO_ADC=1 bash run/dock.sh -- python3 $D/m10.py checkout $SMOKE_BUGS
  log "smoke: container selftest"; in_box selftest
  log "smoke: env"; M10_NET=1 bash $D/dock10.sh python3 -W ignore $D/m10.py env --jobs "$JOBS" $SMOKE_BUGS
  log "smoke: vertexcheck"; with_llm vertexcheck
  for a in $NEW; do log "smoke: gen $a"; with_llm gen $a --jobs "$JOBS" 3 33 53; done
  log "smoke: fix"; in_box fix A0 $NEW --jobs "$JOBS" --bugs $SMOKE_BUGS
  python3 $D/analyze.py A | tee $D/out/smoke_analysisA.txt
  python3 $D/m10.py docs A2 3 33 53
  tests m10_A2_smoke 3
  evaluate m10_A2_smoke
  python3 $D/m10.py cost
  log "smoke done" ;;
phaseA)
  log "phaseA: checkout (no-op when complete)"; NO_ADC=1 bash run/dock.sh -- python3 $D/m10.py checkout
  log "phaseA: env"; M10_NET=1 bash $D/dock10.sh python3 -W ignore $D/m10.py env --jobs "$JOBS"
  for a in $NEW; do log "phaseA: gen $a"; with_llm gen $a --jobs "$JOBS"; done
  log "phaseA: fix"; in_box fix A0 $NEW --jobs "$JOBS"
  python3 $D/m10.py cost
  log "phaseA done; next: run.sh analyzeA" ;;
analyzeA)
  python3 $D/analyze.py A | tee $D/out/analysisA.txt ;;
phaseB)
  ARM=${1:-$(cat $D/out/best_arm.txt)}
  log "phaseB: arm $ARM"
  python3 $D/m10.py docs "$ARM"
  tests "m10_$ARM" 78
  evaluate "m10_$ARM"
  log "phaseB done; next: run.sh analyzeB $ARM" ;;
analyzeB)
  ARM=${1:-$(cat $D/out/best_arm.txt)}
  python3 $D/analyze.py B "$ARM" | tee "$D/out/analysisB_$ARM.txt" ;;
*)
  echo "unknown stage $stage"; exit 1 ;;
esac

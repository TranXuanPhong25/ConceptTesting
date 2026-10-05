#!/usr/bin/env bash
# m9 phase B, one stage at a time, every step strictly sequential (one container at a time).
# usage (from EvalAndMitigate/): nohup bash m9_concept_advanced/run.sh <stage> [arm ...] > m9_concept_advanced/out/<stage>.console 2>&1 &
#   stages: smoke (idx 3 33 53: docstrings, tests, evaluation) | docs | tests | evals | fixrate | analyze
#   arms default to: adv_rerun concept placebo
set -euo pipefail
cd "$(dirname "$0")/.."
D=m9_concept_advanced; stage=$1; shift
ARMS=${*:-adv_rerun concept placebo}
DOC=Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m9_
budget() {  # spend so far (logged docstring calls + test-generation estimate) + $1 must stay under the $5 cap
  python3 -c "import sys; sys.path.insert(0, '$D'); import m9; t = m9.cost(); assert t + $1 < m9.CAP, f'cap: \${t:.2f} + $1'"
}
case $stage in
smoke)
  for a in $ARMS; do bash run/dock.sh -- python3 -W ignore $D/m9.py gen $a 3 33 53; done
  for a in $ARMS; do budget 0.1; DOC_FILE=${DOC}${a}_smoke.jsonl WITH_CODE=0 FILE_POST_FIX=m9_${a}_smoke bash run/dock.sh gen_env; done
  for a in $ARMS; do NO_ADC=1 FILE_POST_FIX=m9_${a}_smoke bash run/dock.sh eval_env; python3 run/summarize.py "$(python3 -c "import sys; sys.path.insert(0, '$D'); from eval_parts import latest_log; print(latest_log('m9_${a}_smoke'))")"; done ;;
docs)
  for a in $ARMS; do bash run/dock.sh -- python3 -W ignore $D/m9.py gen $a; done ;;
tests)
  for a in $ARMS; do budget 1.1; DOC_FILE=${DOC}${a}.jsonl WITH_CODE=0 FILE_POST_FIX=m9_$a bash run/dock.sh gen_env; done
  python3 $D/m9.py cost ;;
evals)
  for a in $ARMS; do python3 $D/eval_parts.py m9_$a; done ;;  # eval_parts.py sets NO_ADC=1
fixrate)
  bash $D/dock9.sh python3 -W ignore $D/fixrate.py check
  for a in $ARMS; do bash $D/dock9.sh python3 -W ignore $D/fixrate.py run $a; done ;;
analyze)
  python3 $D/analyze.py > $D/out/analysis.txt; cat $D/out/analysis.txt ;;
*) echo "unknown stage $stage"; exit 1 ;;
esac

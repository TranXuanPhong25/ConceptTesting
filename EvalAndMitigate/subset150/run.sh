#!/usr/bin/env bash
# subset150 stages (host), strictly one container at a time.
# usage (from EvalAndMitigate/): nohup bash subset150/run.sh <stage> [args] > subset150/out/<stage>.console 2>&1 &
#   sample [Project ...] | final | docs [arm ...] | tests [arm ...] | evals [arm ...] | analyze
#   arms: onlydoc adv rerun concept placebo
set -euo pipefail
cd "$(dirname "$0")/.."
D=subset150; stage=$1; shift
ARMS=${*:-onlydoc adv rerun concept placebo}
M=Gemini-2-5-flash_buggy_source_data_unified_invoked_with
doc_file() { case $1 in onlydoc) echo ${M}_docstring_s150new.jsonl ;; adv) echo ${M}_advanced_docstring_base_cot_code_s150new.jsonl ;;
  rerun) echo ${M}_s150_m9_adv_rerun.jsonl ;; concept) echo ${M}_s150_m9_concept.jsonl ;; placebo) echo ${M}_s150_m9_placebo.jsonl ;; esac; }
budget() {  # spend so far + the reserve $1 must stay under the cap (calllog.py also stops every call at the cap)
  python3 -c "import sys; sys.path.insert(0, '$D'); import calllog as c; t = c.total(); assert t + $1 < c.CAP, f'cap: \${t:.2f} + $1'"
}
host_free() {  # stop below 30 GB free on the host disk (Docker's disk image lives there)
  local g; g=$(df -g / | awk 'NR==2 {print $4}'); echo "host free ${g} GB"; [ "$g" -ge 30 ]
}
case $stage in
sample)
  for p in ${*:-Time Jsoup Compress Math JacksonDatabind Closure}; do
    host_free; NO_ADC=1 bash run/dock.sh -- bash $D/s150.sh sample $p; docker system df | sed -n 1,5p
  done ;;
final)
  NO_ADC=1 bash run/dock.sh -- bash $D/s150.sh final
  NO_ADC=1 bash run/dock.sh -- bash $D/s150.sh labels
  NO_ADC=1 bash run/dock.sh -- python3 -W ignore $D/m9new.py prompts ;;  # m9's leak check on the new prompts (no LLM)
docs)
  for a in $ARMS; do
    case $a in
      onlydoc) budget 0.5; bash run/dock.sh -- bash $D/s150.sh docs_basic ;;
      adv) budget 3; bash run/dock.sh -- bash $D/s150.sh docs_adv ;;
      rerun) budget 3; bash run/dock.sh -- bash $D/s150.sh docs_m9 adv_rerun ;;
      concept|placebo) budget 3; bash run/dock.sh -- bash $D/s150.sh docs_m9 $a ;;
    esac
  done
  python3 $D/calllog.py total ;;
tests)
  for a in $ARMS; do budget 1.5; bash run/dock.sh -- bash $D/s150.sh tests "$(doc_file $a)" s150_$a; done
  python3 $D/calllog.py total ;;
evals)
  for a in $ARMS; do python3 $D/eval_parts.py s150_$a; done ;;  # eval_parts.py sets NO_ADC=1
analyze)
  python3 $D/analyze.py > $D/out/analysis.txt; cat $D/out/analysis.txt ;;
*) echo "unknown stage $stage"; exit 1 ;;
esac

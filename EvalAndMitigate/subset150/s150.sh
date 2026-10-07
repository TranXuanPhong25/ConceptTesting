#!/usr/bin/env bash
# subset150 steps inside the container (bash run/dock.sh -- bash subset150/s150.sh <step> [args]).
# Same notebooks, cells and settings as run/pipeline.sh; differences: this folder's .ovr files where the upstream ones
# would overwrite the 78-method files, generated scripts under subset150/out/nb, LLM scripts run through calllog.py.
set -euo pipefail
cd /repo
export TGT_MODEL=${TGT_MODEL:-Gemini-2-5-flash} VERSION=buggy
D=subset150; NBD=$D/out/nb; mkdir -p $NBD
NEW=data/prompts/buggy_source_data_unified_invoked_s150new.jsonl

nb() {  # notebook keep-cells override name [calllog stage tag]  (run/pipeline.sh's nb, optionally logged)
  python3 run/nb2py.py "$1" "$NBD/$4.py" "$2" "$3"
  if [ -n "${5:-}" ]; then python3 $D/calllog.py "$5" "$NBD/$4.py"; else python3 "$NBD/$4.py"; fi 2>&1 | tee "$NBD/$4.log"
}

step=$1; shift
case $step in
sample) python3 $D/sample.py run "$@" ;;
final) python3 $D/sample.py final ;;
labels) python3 $D/labels_new.py ;;
docs_basic)  # Only Doc arm: run/pipeline.sh docstring_basic
  S150_SRC=$NEW S150_DOC_OUT=data/prompts/${TGT_MODEL}_buggy_source_data_unified_invoked_with_docstring_s150new.jsonl \
    nb Docstring_Generation.ipynb 0,2,4-8,18-22 $D/docstring.ovr docstring_basic docs_basic ;;
docs_adv)  # Advanced arm: run/pipeline.sh docstring_advanced
  S150_SRC=$NEW S150_DOC_OUT=data/prompts/${TGT_MODEL}_buggy_source_data_unified_invoked_with_advanced_docstring_base_cot_code_s150new.jsonl \
    nb Advanced_Docstring_Generation.ipynb 0,2,4-8,18-20,22-23 $D/docstring.ovr docstring_advanced docs_adv ;;
docs_m9) python3 -W ignore $D/m9new.py gen "$1" ;;  # adv_rerun | concept | placebo
prompts_m9) python3 -W ignore $D/m9new.py prompts ;;
tests)  # <DOC_FILE in data/prompts> <FILE_POST_FIX>: run/pipeline.sh gen_cfg with WITH_CODE=0 (Only Doc / Advanced test prompt)
  export DOC_FILE=$1 WITH_CODE=0 FILE_POST_FIX=$2
  nb generate_prompt.ipynb 0-2 run/prompt.ovr prompt_$2
  nb UT_Test_Generation.ipynb 0-2,4-5,8-10,12-13,27,29,31-35,37-40 run/testgen.ovr testgen_$2 "testgen_$2" ;;
*) echo "unknown step $step"; exit 1 ;;
esac

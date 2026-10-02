#!/usr/bin/env bash
# Runs inside the container via run/dock.sh <step>...
set -euo pipefail
cd /repo
export TGT_MODEL=${TGT_MODEL:-Gemini-2-5-flash} VERSION=buggy
PROJECTS=${PROJECTS:-"Lang Cli Csv Codec Gson"}
OUT=run/out; mkdir -p $OUT

nb() {  # notebook keep-cells override|- name
  python3 run/nb2py.py "$1" "$OUT/$4.py" "$2" ${3/#-/}
  (cd /repo && python3 "$OUT/$4.py") 2>&1 | tee "$OUT/$4.log"
}

checkout() {
  for p in $PROJECTS; do ls data/d4j2_fix_info | grep "^${p}_[0-9]*$"; done | xargs -P 1 -I{} bash -c '
    b={}; p=${b%_*}; id=${b##*_}; d=d4j_proj_base/$b
    for v in buggy fixed; do
      [ -d $d/$v ] && continue
      defects4j checkout -p $p -v ${id}${v:0:1} -w $d/$v >/dev/null 2>&1 || { echo "checkout failed: $b $v"; rm -rf $d/$v; }
    done'
  ls d4j_proj_base | wc -l
}

source_data() {
  for v in buggy fixed; do VERSION=$v nb generate_source_data_for_prompt.ipynb 0-4,8,75,77-86 run/gen_src.ovr gen_src_$v; done
  nb unify_fixed_and_buggy_bugs.ipynb 0-30 - unify
}

docstring_basic() { nb Docstring_Generation.ipynb 0,2,4-8,18-22 run/docstring.ovr docstring_basic; }
docstring_advanced() { nb Advanced_Docstring_Generation.ipynb 0,2,4-8,18-20,22-23 run/docstring.ovr docstring_advanced; }
docstrings() { docstring_basic; docstring_advanced; }

DOC_CODE="${TGT_MODEL}_buggy_source_data_unified_invoked_with_docstring.jsonl 1 unified_invoked_docstring_code_prompt"
ADV_DOC="${TGT_MODEL}_buggy_source_data_unified_invoked_with_advanced_docstring_base_cot_code.jsonl 0 unified_invoked_advanced_docstring_prompt"

gen_cfg() {  # args: doc_file with_code file_post_fix
  export DOC_FILE=$1 WITH_CODE=$2 FILE_POST_FIX=$3
  nb generate_prompt.ipynb 0-2 run/prompt.ovr prompt_$3
  nb UT_Test_Generation.ipynb 0-2,4-5,8-10,12-13,27,29,31-35,37-40 run/testgen.ovr testgen_$3
}
eval_cfg() {  # evals share checkouts: never run two at once
  export FILE_POST_FIX=$3
  nb UT_Compile_and_Test_Project.ipynb 0-10,15,18,20-26,36,45-46,52-55,58,63-70 run/eval.ovr eval_$3
}
doc_code() { gen_cfg $DOC_CODE; eval_cfg $DOC_CODE; }
adv_doc_gen() { gen_cfg $ADV_DOC; }
adv_doc_eval() { eval_cfg $ADV_DOC; }
doc_code_eval() { eval_cfg $DOC_CODE; }
ONLY_DOC="${TGT_MODEL}_buggy_source_data_unified_invoked_with_docstring.jsonl 0 unified_invoked_docstring_prompt"
only_doc() { gen_cfg $ONLY_DOC; eval_cfg $ONLY_DOC; }
# generic steps for the m*_ method folders: take DOC_FILE, WITH_CODE, FILE_POST_FIX from the environment
gen_env() { gen_cfg "$DOC_FILE" "$WITH_CODE" "$FILE_POST_FIX"; }
eval_env() { eval_cfg x x "$FILE_POST_FIX"; }

for step in "$@"; do $step; done

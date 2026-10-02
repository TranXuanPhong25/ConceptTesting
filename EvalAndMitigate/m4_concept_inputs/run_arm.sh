#!/usr/bin/env bash
# test generation -> evaluation (resumed after crashes) for one arm. usage: bash m4_concept_inputs/run_arm.sh <concept|placebo>
# the doc files come from `python3 m4_concept_inputs/inputs.py` (deterministic, no LLM)
set -euo pipefail
cd "$(dirname "$0")/.."
arm=$1; fpf=m4_${arm}_inputs; out=m4_concept_inputs/out
DOC_FILE=Gemini-2-5-flash_buggy_source_data_unified_invoked_with_$fpf.jsonl WITH_CODE=0 FILE_POST_FIX=$fpf bash run/dock.sh gen_env > $out/gen_$arm.console 2>&1
python3 m4_concept_inputs/eval_parts.py $fpf > $out/eval_parts_$arm.out 2>&1

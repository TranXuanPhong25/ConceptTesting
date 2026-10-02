#!/usr/bin/env bash
# spec generation -> test generation -> evaluation (resumed after crashes) for one arm.
# usage: bash m5_blind_concept_spec/run_arm.sh <blind_concept|blind_concept_javadoc>
set -euo pipefail
cd "$(dirname "$0")/.."
arm=$1; fpf=m5_$arm; out=m5_blind_concept_spec/out
bash run/dock.sh -- python3 m5_blind_concept_spec/spec.py $arm > $out/spec_$arm.console 2>&1
DOC_FILE=Gemini-2-5-flash_buggy_source_data_unified_invoked_with_$fpf.jsonl WITH_CODE=0 FILE_POST_FIX=$fpf bash run/dock.sh gen_env > $out/gen_$arm.console 2>&1
python3 m5_blind_concept_spec/eval_parts.py $fpf > $out/eval_parts_$arm.out 2>&1

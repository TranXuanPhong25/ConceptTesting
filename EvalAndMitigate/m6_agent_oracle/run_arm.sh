#!/usr/bin/env bash
# docstrings -> test generation -> evaluation (resumed after crashes) for one arm; questions and answers must exist.
# usage: bash m6_agent_oracle/run_arm.sh <oracle_blind|oracle_sees_code> [gen|eval]   (default: both)
set -euo pipefail
cd "$(dirname "$0")/.."
arm=$1; fpf=m6_$arm; out=m6_agent_oracle/out
if [ "${2:-gen}" = gen ]; then
  python3 m6_agent_oracle/oracle.py docs $arm > $out/docs_$arm.console 2>&1
  DOC_FILE=Gemini-2-5-flash_buggy_source_data_unified_invoked_with_$fpf.jsonl WITH_CODE=0 FILE_POST_FIX=$fpf bash run/dock.sh gen_env > $out/gen_$arm.console 2>&1
fi
if [ "${2:-eval}" = eval ] || [ -z "${2:-}" ]; then
  python3 m6_agent_oracle/eval_parts.py $fpf > $out/eval_parts_$arm.out 2>&1
fi

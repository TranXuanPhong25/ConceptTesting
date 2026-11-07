#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$PROJECT_DIRECTORY"
export PYTHONPATH="$PROJECT_DIRECTORY${PYTHONPATH:+:$PYTHONPATH}"

# Load credentials silently; endpoint URL stays in the private env file.
source scripts/research_env.sh >/dev/null 2>&1

exec final/.venv/bin/python -m final.src.audits.run_prompt_style \
  --cohort final/out/development_groups/boundary/known_bug_10/cohort.json \
  --styles final/review/prompts/prompt_style_v1.json \
  --reuse final/out/boundary_prompt_style3_20261106 "$@"

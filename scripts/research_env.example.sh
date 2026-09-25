#!/usr/bin/env bash
# Copy to scripts/research_env.sh, set the two key variables you need, then run:
#
#   source scripts/research_env.sh  # keeps exports in this terminal
#   # or
#   ./scripts/research_env.sh       # prepares artifact config files only
#
# Do not commit scripts/research_env.sh. It is ignored by .gitignore.
#
# 9router is this repository's OpenAI-compatible gateway. Set its key once.
# Change the URL if your 9router instance is remote rather than local.
export ROUTER_API_KEY="${ROUTER_API_KEY:-PASTE_YOUR_9ROUTER_KEY_HERE}"
export ROUTER_BASE_URL="${ROUTER_BASE_URL:-http://localhost:20128/v1}"
export LLM_MODEL="${LLM_MODEL:-vertex/gemini-3-flash-preview}"

# G2FUZZ and CKGFuzzer are configured from the router values above.
export G2FUZZ_API_KEY="$ROUTER_API_KEY"
export G2FUZZ_BASE_URL="$ROUTER_BASE_URL"
export G2FUZZ_MODEL="$LLM_MODEL"
# G2FUZZ upstream sends requests in bursts. Keep this conservative until you
# know your 9router quota; increase it only after confirming the allowed RPM.
export G2FUZZ_RPM="${G2FUZZ_RPM:-5}"
export G2FUZZ_MAX_RETRIES="${G2FUZZ_MAX_RETRIES:-6}"
export CKGFUZZER_API_KEY="$ROUTER_API_KEY"
export CKGFUZZER_BASE_URL="$ROUTER_BASE_URL"
export CKGFUZZER_ANALYZER_MODEL="$LLM_MODEL"
export CKGFUZZER_CODER_MODEL="$LLM_MODEL"

research_env_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

is_placeholder() {
  [[ -z "$1" || "$1" == PASTE_YOUR_*_HERE ]]
}

if is_placeholder "$G2FUZZ_API_KEY"; then
  echo "G2FUZZ: skipped (set G2FUZZ_API_KEY first)."
else
  g2fuzz_dir="$research_env_dir/.artifacts/g2fuzz"
  if [[ -d "$g2fuzz_dir" ]]; then
    umask 077
    printf '%s\n' "$G2FUZZ_API_KEY" > "$g2fuzz_dir/openai_key.txt"
    printf '{\n  "model": ["%s"]\n}\n' "$G2FUZZ_MODEL" > "$g2fuzz_dir/model_setting.json"
    echo "G2FUZZ: key and model configuration prepared."
  else
    echo "G2FUZZ: skipped (.artifacts/g2fuzz is not cloned yet)."
  fi
fi

if is_placeholder "$CKGFUZZER_API_KEY"; then
  echo "CKGFuzzer: skipped (set CKGFUZZER_API_KEY first)."
else
  ckg_dir="$research_env_dir/.artifacts/ckgfuzzer/fuzzing_llm_engine/external_database"
  if [[ -d "$ckg_dir" ]]; then
    export CKGFUZZER_API_KEY CKGFUZZER_BASE_URL CKGFUZZER_ANALYZER_MODEL CKGFUZZER_CODER_MODEL
    while IFS= read -r config; do
      python3 - "$config" <<'PY'
import json
import os
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
section = None
output = []
for line in path.read_text().splitlines(keepends=True):
    heading = re.match(r"^(llm_analyzer|llm_coder):\s*$", line.strip())
    if heading:
        section = heading.group(1)
    elif re.match(r"^[A-Za-z_][A-Za-z0-9_]*:\s*$", line.strip()):
        section = None
    indent = re.match(r"^(\s*)", line).group(1)
    if re.match(r"^\s*api_key:\s*", line):
        line = f"{indent}api_key: {json.dumps(os.environ['CKGFUZZER_API_KEY'])}\n"
    elif re.match(r"^\s*base_url:\s*", line):
        line = f"{indent}base_url: {json.dumps(os.environ['CKGFUZZER_BASE_URL'])}\n"
    elif section == "llm_analyzer" and re.match(r"^\s*model:\s*", line):
        line = f"{indent}model: {json.dumps(os.environ['CKGFUZZER_ANALYZER_MODEL'])}\n"
    elif section == "llm_coder" and re.match(r"^\s*model:\s*", line):
        line = f"{indent}model: {json.dumps(os.environ['CKGFUZZER_CODER_MODEL'])}\n"
    output.append(line)
path.write_text("".join(output))
PY
    done < <(find "$ckg_dir" -mindepth 2 -maxdepth 2 -name config.yaml -type f | sort)
    echo "CKGFuzzer: key and base-URL configuration prepared for shipped targets."
  else
    echo "CKGFuzzer: skipped (.artifacts/ckgfuzzer is not cloned yet)."
  fi
fi

unset research_env_dir g2fuzz_dir ckg_dir config

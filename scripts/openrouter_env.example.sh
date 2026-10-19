#!/usr/bin/env bash
# Copy this file to scripts/openrouter_env.sh, put your real key there, then source it:
#   source scripts/openrouter_env.sh
#
# Do not commit scripts/openrouter_env.sh. It is ignored by .gitignore.

export OPENROUTER_BASE_URL="${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}"
export OPENROUTER_API_KEY="PASTE_YOUR_OPENROUTER_KEY_HERE"
export OPENROUTER_MODEL="${OPENROUTER_MODEL:-qwen/qwen3.5-35b-a3b}"
# Optional hard stop for one run, in USD (the client refuses new calls after this much reported cost).
export OPENROUTER_MAX_USD="${OPENROUTER_MAX_USD:-5}"

echo "Loaded OpenRouter env: OPENROUTER_MODEL=${OPENROUTER_MODEL}, OPENROUTER_MAX_USD=${OPENROUTER_MAX_USD}, OPENROUTER_API_KEY=<hidden>"

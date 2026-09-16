#!/usr/bin/env bash
# Copy this file to scripts/router_env.sh, put your real key there, then source it:
#   source scripts/router_env.sh
#
# Do not commit scripts/router_env.sh. It is ignored by .gitignore.

export LLM_PROVIDER="${LLM_PROVIDER:-router}"
export ROUTER_BASE_URL="${ROUTER_BASE_URL:-http://localhost:20128/v1}"
export ROUTER_API_KEY="PASTE_YOUR_ROUTER_KEY_HERE"

# Optional: set your default router model here if you use one consistently.
# export LLM_MODEL="${LLM_MODEL:-vertex/gemini-3-flash-preview}"

echo "Loaded router env: LLM_PROVIDER=${LLM_PROVIDER}, ROUTER_BASE_URL=${ROUTER_BASE_URL}, ROUTER_API_KEY=<hidden>"

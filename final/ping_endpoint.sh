#!/usr/bin/env bash
# Ping /models and a 1-token completion every 20 minutes. Ctrl+C to stop.
set -euo pipefail

PROJECT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENDPOINT_CONFIG="${1:-${FINAL_ENDPOINT_ENV_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/concepttester/final-qwen.env}}"

if [[ ! -f "$ENDPOINT_CONFIG" ]]; then
  echo "Endpoint config missing; pass its path as the first argument." >&2
  exit 1
fi

source "$ENDPOINT_CONFIG" >/dev/null 2>&1
export QWEN_BASE_URL="${FINAL_BASE_URL:?FINAL_BASE_URL is missing from endpoint config}"
export QWEN_MODEL="${FINAL_MODEL:-qwen3.5-27b-awq}"
export PIDFILE="${PIDFILE:-/tmp/concepttester-final-ping.pid}"

exec bash "$PROJECT_DIRECTORY/scripts/ping_endpoint.sh"

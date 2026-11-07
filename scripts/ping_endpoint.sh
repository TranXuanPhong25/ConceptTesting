#!/usr/bin/env bash
# Keep the Kaggle/ngrok vLLM endpoint alive: every INTERVAL seconds, GET /models and send a 1-token chat completion.
# The URL comes only from the environment (QWEN_BASE_URL, QWEN_MODEL) or an env file given as $1; it is never logged.
#   setsid nohup bash scripts/ping_endpoint.sh <env-file> > <log> 2>&1 &   (stop: kill the PID in $PIDFILE)
# Env: INTERVAL (default 1200 s), PIDFILE (default /tmp/ping_endpoint.pid).
set -u
[ $# -ge 1 ] && source "$1"
: "${QWEN_BASE_URL:?QWEN_BASE_URL not set}"
MODEL="${QWEN_MODEL:-qwen2.5-coder-32b-instruct}"
INTERVAL="${INTERVAL:-1200}"
echo $$ > "${PIDFILE:-/tmp/ping_endpoint.pid}"
while true; do
  models=$(curl -s -o /dev/null -w '%{http_code}' -m 30 "$QWEN_BASE_URL/models")
  chat=$(curl -s -o /dev/null -w '%{http_code}' -m 60 "$QWEN_BASE_URL/chat/completions" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":1}")
  echo "$(date '+%F %T') models=$models chat=$chat"
  sleep "$INTERVAL"
done

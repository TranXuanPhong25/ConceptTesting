#!/usr/bin/env bash
set -euo pipefail
set +x
if [[ "${1:-}" == "--env-file" ]]; then
  source "$2" >/dev/null 2>&1
  shift 2
fi
exec "${V71_PYTHON:-/tmp/concepttester-v57-venv/bin/python}" -B -m trickcatcher_linefacts.pipelines.v71_writercontract.pipeline "$@"

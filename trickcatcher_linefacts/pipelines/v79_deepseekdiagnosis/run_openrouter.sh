#!/usr/bin/env bash
set -euo pipefail
set +x
source scripts/research_env.sh >/dev/null 2>&1
source scripts/openrouter_env.sh >/dev/null 2>&1
exec "${V73_PYTHON:-/tmp/concepttester-v57-venv/bin/python}" -B -m trickcatcher_linefacts.pipelines.v73_ossdiagnosis.oss_probe "$@"

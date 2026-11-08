#!/usr/bin/env bash
set -euo pipefail
RUN_CONSOLE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RUN_CONSOLE_ROOT"
if [[ ! -x final/.venv_orchestration/bin/prefect ]]; then
  uv venv --python final/.venv/bin/python final/.venv_orchestration
  uv pip install --python final/.venv_orchestration/bin/python -r final/src/orchestration/requirements.txt
fi
if [[ $# -eq 0 ]]; then set -- start; fi
exec final/.venv_orchestration/bin/python -m final.src.orchestration.service "$@"

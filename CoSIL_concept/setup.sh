#!/usr/bin/env bash
# Clone CoSIL at the pinned commit, create .venv (Python 3.11 via uv, else python3.10-3.12),
# install deps, verify imports. Idempotent; never uses the system default python3 blindly.
set -euo pipefail
cd "$(dirname "$0")"
COSIL_SHA=0568e423735b399d5b089996961fea9ae142e4c7   # ZhonghaoJiang/CoSIL master, 2026-05-31

if [ ! -d vendor/CoSIL/.git ]; then
  git clone -q https://github.com/ZhonghaoJiang/CoSIL.git vendor/CoSIL
fi
if [ "$(git -C vendor/CoSIL rev-parse HEAD)" != "$COSIL_SHA" ]; then
  git -C vendor/CoSIL fetch -q origin
  git -C vendor/CoSIL checkout -q --detach "$COSIL_SHA"
fi
git -C vendor/CoSIL diff --quiet || { echo "vendor/CoSIL has local edits; the authors' code must stay pristine" >&2; exit 1; }
echo "[setup] CoSIL at $(git -C vendor/CoSIL rev-parse HEAD)"

if [ ! -x .venv/bin/python ]; then
  if command -v uv >/dev/null; then
    uv venv -q --python "${COSIL_PYTHON:-3.11}" .venv
  else
    PY=""
    for c in python3.11 python3.12 python3.10; do command -v "$c" >/dev/null && { PY=$c; break; }; done
    [ -n "$PY" ] || { echo "need uv or python3.10-3.12" >&2; exit 1; }
    "$PY" -m venv .venv
  fi
fi
.venv/bin/python -c 'import sys; assert (3,10) <= sys.version_info[:2] <= (3,12), sys.version' \
  || { echo ".venv python is not 3.10-3.12; rm -rf .venv and retry" >&2; exit 1; }
if command -v uv >/dev/null; then
  uv pip install -q --python .venv/bin/python -r requirements.txt
else
  .venv/bin/python -m pip install -q --upgrade pip && .venv/bin/python -m pip install -q -r requirements.txt
fi
.venv/bin/python cosil_concept.py selftest
echo "[setup] ok: $(.venv/bin/python --version), $(uname -m)"

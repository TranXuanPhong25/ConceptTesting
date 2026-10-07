#!/usr/bin/env bash
# Clone CoverUp and the CodaMosa benchmark sources at pinned commits into vendor/ (never edited), create .venv
# (Python 3.11 via uv, else python3.10-3.12), install pinned deps, run the selftest. Idempotent.
set -euo pipefail
cd "$(dirname "$0")"
COVERUP_SHA=d9ca25b9282621d2779560f2be397ab0683a6733    # plasma-umass/coverup main, 2026-04-05 (v0.6.3)
CODAMOSA_SHA=17a4c2a2ecb40b60e32a7e4a437db03573612f11   # plasma-umass/codamosa, the submodule pinned by coverup-eval@f3173196

pin() {  # dir url sha [sparse paths...]
  local dir=$1 url=$2 sha=$3; shift 3
  if [ ! -d "$dir/.git" ]; then
    if [ $# -gt 0 ]; then   # benchmark sources only: the codamosa repo is ~0.5 GB
      git clone -q --filter=blob:none --no-checkout --sparse "$url" "$dir"
      git -C "$dir" sparse-checkout set --no-cone "$@"
      git -C "$dir" checkout -q --detach "$sha"
    else
      git clone -q "$url" "$dir"
    fi
  fi
  [ $# -gt 0 ] && git -C "$dir" sparse-checkout set --no-cone "$@"   # picks up subset changes
  if [ "$(git -C "$dir" rev-parse HEAD 2>/dev/null)" != "$sha" ]; then
    git -C "$dir" fetch -q origin
    git -C "$dir" checkout -q --detach "$sha"
  fi
  git -C "$dir" diff --quiet || { echo "$dir has local edits; vendor code must stay pristine" >&2; exit 1; }
  echo "[setup] $dir at $(git -C "$dir" rev-parse HEAD)"
}
mkdir -p vendor
pin vendor/coverup https://github.com/plasma-umass/coverup.git $COVERUP_SHA
apps=$(cut -d, -f1 data/subset.csv | sort -u | sed 's|^|/replication/|')
pin vendor/codamosa https://github.com/plasma-umass/codamosa.git $CODAMOSA_SHA /replication/test-apps/cm_modules.csv $apps

if [ ! -x .venv/bin/python ]; then
  if command -v uv >/dev/null; then
    uv venv -q --python "${CU_PYTHON:-3.11}" .venv
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
.venv/bin/python cu_concept.py selftest
echo "[setup] ok: $(.venv/bin/python --version), $(uname -m)"

#!/usr/bin/env bash
# One-time setup: pinned JitVul checkout + CPU-only venv + dataset check. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

JITVUL_URL=https://github.com/alperen21/JitVul
JITVUL_SHA=00e8f9ad6a74cac59a21354da093a6845af7b1af   # only commit on the repo (2025-02-14)

if [ ! -d vendor/JitVul/.git ]; then
  git clone --quiet "$JITVUL_URL" vendor/JitVul
fi
git -C vendor/JitVul checkout --quiet "$JITVUL_SHA"
test "$(git -C vendor/JitVul rev-parse HEAD)" = "$JITVUL_SHA" || { echo "JitVul SHA mismatch"; exit 1; }

# Never the system python3 (may be 3.13+): tree-sitter-languages 1.9.1 has wheels for CPython <=3.12 only.
# uv downloads 3.11 if missing. All pinned packages ship x86_64-linux and arm64-mac wheels: no compiler needed.
if [ ! -x .venv/bin/python ]; then
  if command -v uv >/dev/null && uv venv --quiet --python 3.11 .venv; then :
  elif command -v python3.10 >/dev/null; then python3.10 -m venv .venv
  else echo "need uv (preferred) or python3.10"; exit 1; fi
fi
# tree-sitter pins = ConceptCoder_org/requirements.txt; tree-sitter-languages 1.10.x ships a newer C++ grammar
# whose subscript_expression shape crashes the official utils_VD.get_indices.
# ide arm: flawfinder (pure Python) + cppcheck 2.20.0 as a binary wheel (manylinux_2_28 x86_64 / macOS arm64), no root.
PKGS="google-genai==2.23.0 tree-sitter==0.20.4 tree-sitter-languages==1.9.1 pandas==2.2.3 flawfinder==2.0.20 cppcheck==1.5.2"
if command -v uv >/dev/null; then uv pip install --quiet --python .venv/bin/python $PKGS
else .venv/bin/python -m pip install --quiet --upgrade pip && .venv/bin/python -m pip install --quiet $PKGS; fi

.venv/bin/python harness.py check

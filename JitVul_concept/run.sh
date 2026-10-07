#!/usr/bin/env bash
# Driver: setup | annotate | smoke | run <arm|all> | verify | analyze. Every step is idempotent and resumable.
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
ARMS="base concept placebo callee_code ide"   # ide last (added later)

vertex() {  # Vertex settings: the repo's (gitignored) helper if present, else already-exported env. Values never echoed.
  if [ -f ../scripts/vertex_env.sh ]; then source ../scripts/vertex_env.sh >/dev/null; fi
  if [ -z "${VERTEX_PROJECT:-${GOOGLE_CLOUD_PROJECT:-}}" ]; then echo "set VERTEX_PROJECT (and VERTEX_LOCATION)"; exit 1; fi
}

case "${1:-}" in
  setup) ./setup.sh ;;
  annotate) $PY harness.py annotate && $PY harness.py ide ;;
  verify) $PY harness.py verify ;;
  smoke)
    vertex
    for a in $ARMS; do $PY harness.py run "$a" --smoke; done
    $PY harness.py show concept
    $PY analyze.py ;;
  run)
    vertex
    arm="${2:?usage: $0 run base|concept|placebo|callee_code|ide|all}"
    [ "$arm" = all ] && arm=$ARMS
    for a in $arm; do $PY harness.py run "$a"; done ;;
  analyze) $PY analyze.py ;;
  *) echo "usage: $0 setup | annotate | smoke | run <base|concept|placebo|callee_code|ide|all> | verify | analyze"; exit 1 ;;
esac

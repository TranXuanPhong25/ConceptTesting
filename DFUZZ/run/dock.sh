#!/usr/bin/env bash
# usage: [NOCREDS=1] bash run/dock.sh <command...>
# Runs in dfuzz-pilot:arm64 (native arm64). DFUZZ tree read-only at /dfuzz, only run/ writable. Vertex via ADC
# (gcloud dir mounted read-only). NOCREDS=1 for executor-only steps: no credentials in the container at all.
# VERTEX_PROJECT / VERTEX_LOCATION are passed by name only (values never printed).
D="$(cd "$(dirname "$0")/.." && pwd)"
source "$D/../scripts/vertex_env.sh" >/dev/null
CREDS=(-v "$HOME/.config/gcloud":/gcloud:ro -e GOOGLE_APPLICATION_CREDENTIALS=/gcloud/application_default_credentials.json
       -e VERTEX_PROJECT -e VERTEX_LOCATION)
[ "${NOCREDS:-0}" = 1 ] && CREDS=()
exec docker run --rm -i --memory "${DOCK_MEM:-6g}" --ulimit core=0 --cap-add SYS_PTRACE \
  -v "$D":/dfuzz:ro -v "$D/run":/dfuzz/run "${CREDS[@]}" \
  -e BUDGET_CAP -e PHASE_CAP -e WORKERS -e ORACLE_TIMEOUT -e PYTHONUNBUFFERED=1 \
  -w /dfuzz dfuzz-pilot:arm64 "$@"

#!/usr/bin/env bash
# usage (from PBT_EdgeCases/): [MODE=exec|net|llm] bash run/dock.sh <command...>
# Image pbt-edge:arm64 (native arm64). vendor/ is always mounted read-only at /vendor.
#   exec (default): runs LLM-written tests. NO credentials, --network none, run/ read-only at /work, only run/results
#         writable, mounted at /out (not nested under /work: a nested rw mount under a ro parent turned read-only
#         mid-run on Docker Desktop while the llm container was writing into run/).
#   net : dataset download only (network, no credentials, executes no generated code).
#   llm : Vertex calls only (ADC read-only + VERTEX_PROJECT/LOCATION by name; never executes generated code).
set -e
D="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${MODE:-exec}"
COMMON=(--rm -i --memory "${DOCK_MEM:-4g}" --pids-limit 512 --ulimit core=0 -v "$D/vendor/ebt_pbt_test":/vendor:ro -w /work)
case "$MODE" in
  exec) mkdir -p "$D/run/results"
        exec docker run "${COMMON[@]}" --network none -v "$D/run":/work:ro -v "$D/run/results":/out \
          -e WORKERS -e ONLY -e REPAIR pbt-edge:arm64 "$@" ;;
  net)  exec docker run "${COMMON[@]}" -v "$D/run":/work pbt-edge:arm64 "$@" ;;
  llm)  source "$D/../scripts/vertex_env.sh" >/dev/null
        exec docker run "${COMMON[@]}" -v "$D/run":/work \
          -v "$HOME/.config/gcloud":/gcloud:ro -e GOOGLE_APPLICATION_CREDENTIALS=/gcloud/application_default_credentials.json \
          -e VERTEX_PROJECT -e VERTEX_LOCATION -e BUDGET_CAP -e K -e ARMS -e ONLY pbt-edge:arm64 "$@" ;;
  *) echo "bad MODE" >&2; exit 2 ;;
esac

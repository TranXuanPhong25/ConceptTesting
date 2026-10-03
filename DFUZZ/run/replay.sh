#!/usr/bin/env bash
# Replay all 37 DFUZZ reproducers on native arm64 CPU. Original tree mounted read-only; only run/ is writable.
set -euo pipefail
D="$(cd "$(dirname "$0")/.." && pwd)"
docker image inspect dfuzz:arm64 >/dev/null 2>&1 || docker build -t dfuzz:arm64 -f "$D/docker/Dockerfile" "$D"
docker run --rm --memory 6g --ulimit core=0 -e TIMEOUT="${TIMEOUT:-60}" -e REPS="${REPS:-3}" \
  -v "$D":/dfuzz:ro -v "$D/run":/dfuzz/run dfuzz:arm64 /opt/py38/bin/python /dfuzz/run/replay.py

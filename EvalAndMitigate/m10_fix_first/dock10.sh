#!/usr/bin/env bash
# m10 sandbox (m9's dock9.sh pattern) for everything that compiles or runs Java: no gcloud credentials (the NO_ADC=1
# equivalent), no network, the repo read-only, outputs only through /m10out (= m10_fix_first/out, M10_OUT), the
# Defects4J checkouts (volume d4jproj) read-only at /d4j, scratch copies in the named volume m10scratch (/scratch).
# M10_NET=1 keeps the network: used only by `m10.py env`, which compiles the developers' own code with defects4j.
# usage (from EvalAndMitigate/): bash m10_fix_first/dock10.sh <command...>
cd "$(dirname "$0")/.."
mkdir -p m10_fix_first/out
NET=(--network none); [ -n "${M10_NET:-}" ] && NET=()
exec docker run --rm "${NET[@]}" -v "$PWD":/repo:ro -v "$PWD/m10_fix_first/out":/m10out -e M10_OUT=/m10out \
  -v d4jproj:/d4j:ro -v m10scratch:/scratch evalmitigate "$@"

#!/usr/bin/env bash
# m9 sandbox (copy of m8_concept_mutants/dock8.sh, paths moved): for compiling/running LLM-written Part 2 code.
# No gcloud credentials (NO_ADC=1 equivalent), no network, repo read-only except m9_concept_advanced/out,
# d4jproj checkouts READ-ONLY (also at /d4j, which avoids the bind-mount ENOENT flakiness), scratch in volume m9scratch.
# Outputs are written through /m9out (M9_OUT), a top-level mount of the same folder (m8's final pattern: a nested
# mount once went read-only).
# usage (from EvalAndMitigate/): bash m9_concept_advanced/dock9.sh <command...>
cd "$(dirname "$0")/.."
exec docker run --rm --network none -v "$PWD":/repo:ro -v "$PWD/m9_concept_advanced/out":/repo/m9_concept_advanced/out \
  -v "$PWD/m9_concept_advanced/out":/m9out -e M9_OUT=/m9out \
  -v d4jproj:/repo/d4j_proj_base:ro -v d4jproj:/d4j:ro -v m9scratch:/scratch evalmitigate "$@"

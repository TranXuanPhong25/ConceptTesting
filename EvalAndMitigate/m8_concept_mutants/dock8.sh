#!/usr/bin/env bash
# m8 sandbox for everything that compiles or runs mutated or LLM-written Java (and for the offline analysis):
# no gcloud credentials (the NO_ADC=1 equivalent of run/dock.sh), no network, the repo read-only except
# m8_concept_mutants/out, the d4jproj checkouts READ-ONLY, scratch copies in the named volume m8scratch (/scratch).
# The checkouts are also mounted at /d4j: paths below the /repo bind mount (/repo/d4j_proj_base) hit transient ENOENT
# errors on Docker Desktop (the "cause unknown" crashes of the evaluations); phase0.py and probe.py use /d4j.
# For the same reason the scripts write their outputs through /m8out (M8_OUT), a top-level mount of the same folder.
# usage (from EvalAndMitigate/): bash m8_concept_mutants/dock8.sh <command...>
cd "$(dirname "$0")/.."
exec docker run --rm --network none -v "$PWD":/repo:ro -v "$PWD/m8_concept_mutants/out":/repo/m8_concept_mutants/out \
  -v "$PWD/m8_concept_mutants/out":/m8out -e M8_OUT=/m8out \
  -v d4jproj:/repo/d4j_proj_base:ro -v d4jproj:/d4j:ro -v m8scratch:/scratch -e M8_WORKERS evalmitigate "$@"

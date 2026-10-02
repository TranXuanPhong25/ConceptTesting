#!/usr/bin/env bash
# usage (from EvalAndMitigate/): bash run/dock.sh <pipeline steps...>   |   bash run/dock.sh -- <any command>
# NO_ADC=1: do not mount gcloud credentials (use for evaluation: it executes LLM-written tests)
cd "$(dirname "$0")/.."
if [ "${1:-}" = "--" ]; then shift; CMD=("$@"); else CMD=(bash run/pipeline.sh "$@"); fi
ADC=(-v "$HOME/.config/gcloud":/gcloud:ro -e GOOGLE_APPLICATION_CREDENTIALS=/gcloud/application_default_credentials.json)
[ -n "${NO_ADC:-}" ] && ADC=()
exec docker run --rm -v "$PWD":/repo -v d4jproj:/repo/d4j_proj_base "${ADC[@]}" \
  -e GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)} \
  -e PROJECTS -e TGT_MODEL -e DOC_FILE -e WITH_CODE -e FILE_POST_FIX -e THINKING_BUDGET \
  evalmitigate "${CMD[@]}"

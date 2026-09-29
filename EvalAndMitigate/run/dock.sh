#!/usr/bin/env bash
# usage (from EvalAndMitigate/): bash run/dock.sh <pipeline steps...>
cd "$(dirname "$0")/.."
exec docker run --rm -v "$PWD":/repo -v d4jproj:/repo/d4j_proj_base \
  -v "$HOME/.config/gcloud":/gcloud:ro -e GOOGLE_APPLICATION_CREDENTIALS=/gcloud/application_default_credentials.json \
  -e GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)} \
  -e PROJECTS -e TGT_MODEL -e EVAL_CONFIGS evalmitigate bash run/pipeline.sh "$@"

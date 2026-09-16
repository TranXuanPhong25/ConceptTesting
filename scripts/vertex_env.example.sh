#!/usr/bin/env bash
# Copy to scripts/vertex_env.sh, set the project, then source it.

export LLM_PROVIDER=vertex
export VERTEX_PROJECT=your-google-cloud-project-id
export VERTEX_LOCATION=global
export LLM_MODEL=gemini-3-flash-preview
export LLM_THINKING_BUDGET=0

echo "Loaded native Vertex env: project=${VERTEX_PROJECT}, location=${VERTEX_LOCATION}, model=${LLM_MODEL}"

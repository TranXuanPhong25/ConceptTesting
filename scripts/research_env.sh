#!/usr/bin/env bash
# Local-only research credentials. This file is ignored by Git.
# Fill the variables below, then run `source scripts/research_env.sh`.

export G2FUZZ_API_KEY="sk-e1e0fb1b9a012d77-gudd4y-40045ec8"
export G2FUZZ_BASE_URL="http://localhost:20128/v1"
export G2FUZZ_MODEL="vertex/gemini-3-flash-preview"
export G2FUZZ_PROVIDER_ORDER="google-vertex"
export G2FUZZ_ALLOW_FALLBACKS="false"
export G2FUZZ_HTTP_REFERER=""
export G2FUZZ_APP_TITLE="ConceptTester research"

export CKGFUZZER_API_KEY="sk-e1e0fb1b9a012d77-gudd4y-40045ec8"
export CKGFUZZER_BASE_URL="http://localhost:20128/v1"
export CKGFUZZER_ANALYZER_MODEL="vertex/gemini-3-flash-preview"
export CKGFUZZER_CODER_MODEL="vertex/gemini-3-flash-preview"

# Compatibility with the earlier local file: reuse its existing key and URL
# as the one 9router configuration consumed by every artifact.
export ROUTER_API_KEY="$G2FUZZ_API_KEY"
export ROUTER_BASE_URL="$G2FUZZ_BASE_URL"
export LLM_MODEL="vertex/gemini-3-flash-preview"

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/research_env.example.sh"

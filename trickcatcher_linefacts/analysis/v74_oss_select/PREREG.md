# v74 GPT-OSS-120B concept selection (v47 replay with a stronger model)

Written 2026-10-25 before any v74 model output. User request: "thử với gptoss120b của openrouter xem như nào" after
reviewing the agentic/tool concept-selection line (v21, v40, v43, v47 all no-go with Qwen).

## Question
v47 showed Qwen2.5-Coder-32B picks concept instances from a tool-built menu *below* random (16 vs random3 18.25,
perfect 23). Is that a model-capability limit? v74 changes only the model.

## Fixed from v47 (no change)
- Frozen `out/analysis/v47_concept_select/prepared.json` (menus, instances); copied byte-identical, sha256 checked.
- Prompt builder `select_run.prompt`, parser `select_run.parse_picks`, scorer `select_run.score`, arms
  (spec+code, spec-only), 33 vibepass_half PUTs, temperature 0, seed 20261022. References enter only in scoring.

## Changed
- Model `openai/gpt-oss-120b` via OpenRouter, provider sort by price, reasoning effort `medium`, max_tokens 4096
  (Qwen had 512; reasoning tokens need room). No `response_format` (keeps providers open; the v47 parser already
  extracts ids from free text). Cost hard cap $0.20 from reported usage; every call records provider/usage/cost.
- Output: `out/analysis/v74_oss_select/`.

## Rule (v47 rule, unchanged)
promising iff spec+code covered@3 ≥ random3 + 3 AND covered@3 ≥ 0.5 × perfect_menu. Also reported: spec-only,
first3, kind-matched random, per-kind random, and Qwen v47 numbers side by side. One run, no rerun/prompt tuning.

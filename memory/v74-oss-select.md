---
name: v74-oss-select
description: 2026-10-25 v47 concept selection replayed with GPT-OSS-120B (OpenRouter): no-go, 15/14 vs random 18.25/17.96, Qwen 16/15; $0.0156
metadata:
  type: project
---

`trickcatcher_linefacts/analysis/v74_oss_select/` (PREREG, oss_select.py, RESULTS.md). Same frozen v47 menus, prompt
(sha256-identical), parser and scorer; only the model changed to openai/gpt-oss-120b (reasoning medium, max_tokens
4096, provider sort price → Near AI). spec+code covered@3 15 vs random3 18.25, first3 18, perfect 23 (Qwen 16);
spec-only 14 vs 17.96 (Qwen 15). One truncation (case 61, all reasoning) worth ≤ +1. Cost $0.015635.

**Why:** user asked whether the agentic/tool concept-selection line fails only because Qwen is weak.
**How to apply:** selection-from-menu failure is not model size; do not retry with another model. A new direction
needs a new information source for selection (e.g. dynamic execution feedback per instance), see [[v47-concept-select]],
[[v44-concept-matrix]], [[astra-concept-agent-diagnostic]], [[check-version-tree-before-proposing]].

---
name: v28-codexflow
description: v28 2026-10-18 — full pipeline with tool-less Codex on pilot20: every arm 16–17/20, FA 0–3 (Qwen 1–4, FA 19–38); ceiling, no concept gain
metadata:
  type: project
---

2026-10-18 (Claude): `pipelines/v28_codexflow/`, report `trickcatcher_linefacts/analysis/v28_codexflow_results.md`.
Codex CLI with `--disable shell_tool code_mode_host browser_use computer_use apps` (v27 Codex could run bash in its
read-only sandbox; verified by a SHA-256 probe — always disable tools for model-only comparisons).

- Full pipeline pilot20: all 9 LLM arms 16–17/20 confirmed, 0–3 FA; plain = concept arms (ceiling). No concept gain.
- Oracle without tools: exact_spec .84, property strict 1.00 (pilot20); v27 conclusion (model-limited) holds.
- Caveats: HumanEval memorization; K=1; Codex timeouts happen (300 s × 3) → runner must record, not crash.

**How to apply:** a harder / non-memorized benchmark is needed to see any concept effect with a strong model
(e.g. VibePass, MBPP+ real bugs); with Qwen 7B the oracle dominates. Related: [[v27-codexoracle]].

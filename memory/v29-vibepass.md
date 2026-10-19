---
name: v29-vibepass
description: INVALID (reference leak in prompts) — v29 2026-10-19 — tool-less Codex full pipeline on VibePass 66 PUTs: arms 5–9/66, concept+input+hyp top 9 but more FA; rule not passed; input is the bottleneck
metadata:
  type: project
---

**INVALID:** prompts included `humaneval_mbpp_plus.jsonl` `test` (canonical solution + contract + hidden inputs). Never use
the `_plus` `test` field as prompt-visible base tests; use `humaneval_mbpp.jsonl` `test`.

2026-10-19 (Claude): `pipelines/v29_vibepass/`, report `trickcatcher_linefacts/analysis/v29_vibepass_results.md`.
One-shot held-out run of the frozen v28 config on VibePass (all 66 PUTs buggy, public tests pass).

- Confirmed /66: concept+input+hyp 9 (FA 5), flow+input 8, toolinput 8 (FA 1), plain 7, placebo 6, witness-only 0.
- Paired: c+i+h vs toolinput 1–0, vs plain 3–1, vs placebo 3–0 — but FA higher → registered rule not passed.
- Codex oracle is good (wrong expected 2–6/arm); only 7–9 tasks ever get a bug-exposing admissible input.
- Concept-only arms emit 7–8 contract-invalid inputs; grounded arms ~0.
- Transport lesson: long prompts via argv → E2BIG; send Codex prompt on stdin (`codex exec ... -`).

**How to apply:** with a strong model the next lever is input discovery on VibePass (contract-aware fuzz witnesses,
more discovery budget), not oracle. Related: [[v28-codexflow]], [[v27-codexoracle]].

---
name: round-novelty
description: 2026-10-23 round-novelty (Anthropic code-review blog analog) on saved v11_fair dev — NO SIGNAL; concept round 2 mostly re-finds tool-witness bugs
metadata:
  type: project
---

2026-10-23 (Claude), user asked for ideas from Anthropic's "Solving code review at Anthropic" blog, then said "có" to
the $0 round-novelty check. `trickcatcher_linefacts/analysis/round_novelty_20261023/` (PREREG + amendment 1 after an
independent review, RESULTS.md, results.json, round_novelty.py; RESULTS §11.85).

- Gate: replay equals final_protocol_v11_dev.json. Redundancy share (round 2 re-finds round-1 bug): concept 29%,
  placebo 44%, plain 48%.
- r2_new concept vs placebo 39 vs 39. Input-matched co-primary 35.5 vs 20.5, 16/8, p=.15 → **NO SIGNAL**.
- Same requests but concept yields 354 verified R2 inputs vs placebo 926 (concept hints harder to hit).
- 28/39 concept r2_new on tasks witness-only already detects; beyond-tool 11 vs placebo 23.

Other blog ideas judged prior art: verification/voting (v7 ref, v27, v45, v48/v49), incident eval set (benchmark
itself). Not done: clean-PUT harm check (program-level FA on truly correct PUTs) — needs LLM calls, ask first.

**Why:** closes "concept makes extra rounds find new bugs". **How to apply:** don't propose round-2 concept redesigns
without addressing that concept round 2 duplicates the tool witnesses. Related: [[signal-not-more-data]],
[[check-version-tree-before-proposing]], [[v48-v49-e2e-defn]].

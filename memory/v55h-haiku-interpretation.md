---
name: v55h-haiku-interpretation
description: 2026-10-25 v55 interpretation concept for the defn oracle, Haiku writer: all arms 21/33, 0 FA, identical → not promising (ceiling)
metadata:
  type: project
---
v55 (Codex writer) was stopped after 6/33 calls because each gpt-6.1-sol batch used about 3–4% of the 5h quota. The
user asked to try Haiku, giving v55h: same prompts, 33 Haiku subagents, 264 answers. defn = interpretation = placebo =
**21/33 confirmed tasks, 411 tests, 0 FA, precision 1.0, 0 common-mode problems**. The programs differ, but on valid
inputs every arm's quorum agrees with the reference.

**Why:** the oracle is no longer the bottleneck even with Haiku; the remaining failures are reach/abstention.
**How to apply:** do not spend more on oracle-side concepts for this cohort. Haiku subagents are a cheap writer (they
mislabel file names: validate entrypoints). Related: [[v53-validity-smallscope]], [[v48-v49-e2e-defn]],
[[codex-quota-fallback]]. `trickcatcher_linefacts/analysis/v55h_haiku_interpretation/RESULTS.md`.

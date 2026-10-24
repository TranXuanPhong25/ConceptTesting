---
name: v53-sonnet-tester
description: 2026-10-24 Claude Sonnet as test writer in the v34 fault-concept loop (6 tasks): all arms 5/6, FA 0 → no concept signal; strong model at ceiling
metadata:
  type: project
---

v53 (`trickcatcher_linefacts/analysis/v53_sonnet_tester/`): user asked "spawn claude sonnet làm vài task xem concept có
giúp k". v34 loop unchanged, LLM = one fresh Sonnet subagent per call (file client; prompts byte-identical to Qwen's),
arms plain / fault-template / template-placebo, 6 tasks Qwen failed (141, 39, 56, 36, 132, 70). Result: every arm
confirms the same 5/6 tasks with 0 FA (Qwen same tasks: 3/2/1, FA 2/10/7). Confirmed tests 18 / 25 / 24 — placebo =
concept, so extra tests come from the template inputs, not concept content; 1 test per arm reuses a tool input.

**Why:** with v28 (Codex ceiling) this shows the fault concept is redundant for strong models and did not beat placebo
for weak ones (v34). **How to apply:** don't re-propose "stronger model + same concept"; a concept must carry
information a strong model cannot derive itself (see [[signal-not-more-data]], [[v34-ftplacebo]], [[v47-concept-select]]).
Orchestration recipe (file client + stateless subagent per call, wave reruns, re-validate answers before score) is
reusable. Complements v52 (other session: Sonnet as oracle-program writer).

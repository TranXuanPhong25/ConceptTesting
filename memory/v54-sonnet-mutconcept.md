---
name: v54-sonnet-mutconcept
description: v54 (ex-v53_sonnet_mutconcept) 2026-10-24 Sonnet TC variants on 6 Qwen-failed tasks: 6/6 both arms (ceiling), concept no gain; writer strength is the effect
metadata:
  type: project
---

User 2026-10-24: "thử spawn claude sonnet làm vài task xem nó có tốt hơn không (concept có giúp k)". Pilot
`trickcatcher_linefacts/analysis/v54_sonnet_mutconcept/ (renumbered from v53: collision with v53_sonnet_tester)` (PREREG + Amendments 1–2, RESULTS.md):
- 36 Sonnet subagents (`claude-sonnet-5-5`) wrote the v46 TC variants, k = 3 per arm (`tc` vs `tc_concept`).
- Tasks 85, 141, 46, 65, 101, 161: v42 D1 tasks where every v48 Qwen TC arm failed.
- Result: confirmed 6/6 in both arms. Right programs 18/18 (`tc`) vs 16/18 (`tc_concept`); FA 3 vs 0. No shown mutant
  edit was ever applied.
- Concept: no measurable effect (ceiling). Writer strength is the effect: Sonnet repairs the bug where Qwen variants
  were common-mode.
- Qwen on the same tasks (after the v46 score): k = 10 gives 0/6 (47 valid variants, only 5 differ from the PUT). v52 (other session, definitional concept) asks the same question.

Process lessons:
- Subagent leakage control: one Read of the prompt file plus Write/Edit only to its own answer file, checked from
  the transcript JSONL (`audit`).
- A tool-count rule is too strict: 4/36 agents rewrote their own answer file.

**Why:** this matches v27/v28 (Codex at the ceiling, no concept gain). Concept effects cannot be seen when a strong
writer saturates. With Qwen the oracle fails for model reasons (common-mode), not for lack of concepts.
**How to apply:** do not expect concept gains from a stronger writer on the oracle side. To test concepts, use tasks
where a strong writer still fails, or a weak writer with a placebo control. Related: [[v42-v45-mutoracle]],
[[v48-v49-e2e-defn]], [[v27-codexoracle]], [[signal-not-more-data]].

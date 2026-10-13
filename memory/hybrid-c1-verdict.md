---
name: hybrid-c1-verdict
description: PBT_EdgeCases/hybrid C1 disagreement-input hints (branch claude/ecstatic-davinci-dgzehr) are significant only vs a harmful placebo; C2 cannot reach 33/50/111
metadata:
  node_type: memory
  type: project
  originSessionId: 7ff5ccb6-c822-4e0c-85b2-728de325d857
  modified: 2026-10-09T18:10:42.652Z
---

Data lives on remote branch `origin/claude/ecstatic-davinci-dgzehr`, folder `PBT_EdgeCases/hybrid/`. It has not been merged to main. Setup: 50 TrickCatcher EvalPlus PUTs, Claude Sonnet subagents, 1 sample per arm. I rechecked it on 2026-10-10.

C1 results, per-sample paired sign tests:
- diff_ebt detects 42/50.
- vs plain EBT: 5/2 (p = .45) against sample a, 7/1 (p = .07) against sample b.
- vs EBT with the generic checklist: 5/2 (p = .45).
- vs the rnd placebo: 9/0 (p = .004). The rnd placebo is itself harmful (33 vs 37.5).
- hybrid diff = hybrid generic (42 = 42).
- On the 28 disagreement tasks: vs plain 6/0 (p = .03), vs checklist 4/0 (p = .13).

Noise:
- An A/A comparison of two plain EBT samples gives 4/1.
- On the 22 tasks where the diff and rnd prompts are identical, results still differ 2/0.
- diff_ebt has 8 units that fail on both the PUT and the fixed solution (likely false alarms); other EBT arms have 1–3.

Coverage gaps:
- 33, 50 and 111 have 0 suspicious inputs, so C2 (ambiguity split) cannot target them.
- 55 and 63 are not in the 50 tasks; they come from the 16-bug pilot.
- C5 (n > 2**53) was already in the prompts, and the model ignored it.

My recommendation on 2026-10-10:
- Re-run C1 on 138 PUTs, K = 3, Gemini 2.5 Flash, with plain / checklist / diff / rnd / tool-only arms plus a precision metric (≈ $3–5).
- Make the main concept the execution-verified "gap" family (C4 surviving mutants + C7 untested partitions), using the ConceptCoder BP abstract-value vocabulary, given at an intermediate level with a covered-cell placebo.
- Treat C2, C5 and C6 as case studies.
- The tool-only majority-oracle baseline reuses TrickCatcher's oracle, so AGENTS rule 2 requires asking first. Not yet approved.

**Why:** the user is choosing which concept (C1–C7) to prioritize.

**How to apply:** don't re-derive these stats. Compare any C1 claim against plain / checklist, not against rnd. Related: [[conceptcoder-paper-facts]], [[thesis-concept-requirement]], [[test-aware-mutants-candidate]], [[api-budget]].

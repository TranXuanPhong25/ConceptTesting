---
name: linefacts-v23-diagnostic
description: v23 copied best v7;26 CPU tests, clean-context audit; Luna supplied-concept probe null; Qwen diagnostic16 complete, concept gain not shown
metadata:
  type: project
---

(Codex, 2026-10-17) User authorized copying the best version, code first, then a
clean-context subagent audit of completeness/correctness/practical output. Prefer
libraries where adequate. User optionally requested gpt-6-luna/low to test concept
use, then supplied an endpoint and authorized Qwen launch after code completion.

Read [CPU/audit report](../trickcatcher_linefacts/analysis/v23_cpu_audit.md) and
`pipelines/v23_concepthyp/README.md`/PREREG. Parent is best v7 with hashes, not the
pre-existing untracked v21_flowtools. Originals/frozen versions unchanged.26 CPU
tests and16-case preflight pass; source frozen after audit fixes. Three arms:
concept_chain, direct_chain, hyp_only (exact shared concept-guided hypothesis).

Two clean-context Luna/low supplied-concept/control probe agents completed5 seen
cases. Both catch all3 buggy cases, handle correct unused-operation and ambiguity
correctly; no observed false alarms, no incremental concept advantage. Not Qwen
extraction or benchmark efficacy. Source/raw/protocol/report in analysis/v23_luna_probe.

Qwen diagnostic16 completed normally; source/generation/parent hashes verified. Read
[final report](../trickcatcher_linefacts/analysis/v23_qwen_diagnostic_results.md), RESULTS §11.61.
160 completions,175022 input/28221 output tokens,0 transport errors; all schema-valid.
Correct assertion cases2/7 for all arms; input-discrepancy cases C/D/H=4/5/5. No
incremental concept benefit. Alignment/trigger/oracle reasoning fails despite good
main code summaries; argument/prediction literals also fail on93/288 slots. Correct
mechanism+sufficient trigger only C=f08,D=f08/f16 by independent model-assisted review,
not human gold. Some detections arise despite wrong hypotheses/predicted outputs.
No benchmark promotion, new calls or source repair. Callback handled; nothing to
resume or duplicate. Frozen run under out/pipelines/v23_concepthyp/humaneval/
concept_hypothesis_diagnostic. Endpoint remains environment-only.

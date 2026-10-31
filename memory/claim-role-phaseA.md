---
name: claim-role-phaseA
description: 2026-10-21 claim-role Phase A Gate A STOP (high ROLE only E2); OBS-null probe not supported; binding ablation inconclusive; B1/B2 not run
metadata:
  type: project
---

Phase A of [PLAN_CLAIM_ROLE_SEPARATION](../research/benchmark-papers-2025-2026/audit/PLAN_CLAIM_ROLE_SEPARATION_20261021.md)
done 2026-10-21 in `trickcatcher_linefacts/analysis/claim_role_phaseA_20261021/` (commit 278804d). 24 v40 retry3
episode-arm rows labelled by parent + 2 independent reviewers (one blind to v40 audits).

Result: **Gate A STOP.** Agreed high-confidence ROLE only E2 CA/GA (withdraw ">" keep ">=" = spec wording,
against ([2,2,2],2)->0). Eligible target rows 7 (E2 CA/GA, E4 CA/CC, E6 CA/GA/CC); only 2/7 lack upstream cause:
E4 = ROLE vs OBS unresolved (exception rendered `"output": null` reads like return None), E6 = PRED
(wrong arithmetic/discriminators at T1). E3 = SPEC (binding taken as spec).

**How to apply:** do not run B1/B2 of that plan or re-label to rescue H_role. Side finding worth remembering for any
future tool-feedback renderer: do not show `output: null` next to an exception. User asked 2026-10-21 to "chạy thử"
with the Qwen32B endpoint after Phase A; gate said STOP, user then chose the OBS-null probe
(`analysis/obs_null_probe_20261021/`, commit 0fb924a, 6 calls): removing `output: null` left E4 CA/CC withdrawal +
"return None" predictions unchanged (controls byte-identical to v40) -> **H_obs not supported**; GA correct both.
Post-hoc, untested: only concept arms fail and their packet has binding `allowed_outcome="return None"` — hypothesis (not established; ablation below inconclusive):
packet value leaking into prediction. Gate A NOT reopened; reviving H_role needs a new registered plan.
2026-10-22 concept-binding ablation (`analysis/concept_binding_ablation_20261022/`, commit b2b67d0, 6 calls, fresh
controls byte-identical): removing only `allowed_outcome` changed nothing; removing whole packet fixed CA and removed
"return None" predictions in both CA/CC, but CC still withdrew (polarity-like) -> **inconclusive** per PREREG.
E4 line closed; no more contexts/replicates. Thesis draft section summarizing the chain:
`trickcatcher_linefacts/analysis/thesis_concept_role_negative_20261022.md` (framing: packet normative content leaks into
descriptive slots, E3+E4; role confusion also in GA so not concept-caused). Related:
[[concept-research-autonomy]], [[astra-concept-agent-diagnostic]], [[signal-not-more-data]].

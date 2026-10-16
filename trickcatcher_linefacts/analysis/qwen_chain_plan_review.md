# Qwen chain plan review — 2026-10-16

User asked for a plan; earlier instruction requires independent subagent audit before implementation. Root expanded PLAN_QWEN_REASONING_CHAIN.md before asking two read-only reviewers (`audit_flow_plan`, `audit_experiment_plan`). No implementation, tests, model requests or GPU work in this turn.

| Audit finding | Resolution in final v3 |
|---|---|
| Recovery cannot cite nonexistent upstream IDs | First pilot forbids upstream reconstruction. Missing mandatory predecessor blocks descendants; independent S1/S2 still attempted. S5 revisions have global task/stage/version identity and supersedes links. |
| S2 could miss helper/global semantics or receive normative hints | Freeze executable module context from original bundle, masked docs/comments with original UTF-8 source positions; spec spans separately character-indexed. Missing external context unknown. No inherited concept facts/model labels. |
| Tools could implicitly decide semantics | Open concept vocabulary; no property/effect matcher. Exact-value/status checks only where supported; relation prose stays unverified. Qwen requests source observations, tools cannot select interesting nodes from prose. |
| Feedback could hide counterevidence | Fixed scope/retention/projection; every input-attempt status shown; omissions explicit. Context overflow is failure, no silent counterevidence dropping. |
| Retry/resume consumption unbounded | Max3 cumulative identical attempts/slot,120s timeout,2/8s backoff. No schema/content retries or attempt reset.180 possible logical slots/540 physical attempts; timeout usage may remain unknown. |
| Semantic12/16 gate lacked authority/task rubric | Prewritten critical obligation/effect items and accepted ambiguity; both S1/S2 must cover all critical items without material contradiction. Human adjudication required; model review remains provisional. No adjudication→P2 diagnostic report only. |
| Gate required correct programs to invent mismatches | Replace72/80 and14/16 probe thresholds.62 mandatory slots + optional actually requested,90% stage-validity gate;6/7 predeclared probe-applicable tasks. Legitimate terminals N/A, all80 raw outcomes retained. Applicability labels evaluator-only. |
| Cost equality could be overstated | Scheduled/attempted/successful stages, cache/retries and adaptive probes distinct. Later comparisons match ceilings and interfaces, expose actual differences; claim architecture/package gain only. |

Both reviewers rechecked the v3 contracts and arithmetic:48 mandatory S1–S3 +14 mandatory S4/S5 across7 probe-applicable fixtures =62;18 optional slots;80 total possible. Correct-code/ambiguous/masked/unreachable fixtures may terminate appropriately. Real20 cohort has no gold-informed applicability rule.

Final disposition from both reviewers: accepted plan deliverable, no remaining must-fix blocker within reviewed scope. This is not empirical validation of Qwen performance or authorization to start GPU from a plan-only request. Before any future outputs, exact prompts/schemas/fixture labels/limits are frozen in a new preregistered implementation.

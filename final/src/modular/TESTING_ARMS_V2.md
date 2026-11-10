# Testing arms v2 — code and completed runs

V2 adds behavioral/relational partition refinement, specification-supported fault hypotheses and one short production-domain example per technique. It uses the existing single-completion input generation, shared parser, global input freeze, corrected reference oracle and PUT scorer. It does not add a solver or semantic proof of model annotations.

Available names: `ep_bva_v2`, `decision_table_v2`; v1 names remain available. CLI selects them with `--arms ep_bva_v2 decision_table_v2`; catalogue arms default to4096completion tokens,context8192,20inputs/task,timeout8s. This command starts workload and still requires user authorization. Existing private endpoint profile remains outside the repo.

Implementation: `arms/fault_oriented.py`, `fault_oriented_testing/`, shared `catalogue.py`, `catalogue_reporting.py`, `stages/catalogue_measurement.py`. `arms/classical.py` supplies previously uncommitted v1 integration required by v2. The registered full v2 completed on these runtime bytes; later tool-sampling worktree changes are excluded from this commit.

Examples: [source provenance](../../research/testing_arm_examples/README.md). Plan: [v2 protocol](../../PLAN_TESTING_ARMS_V2.md). Results: [smoke24](../../review/testing_arms_v2_smoke24_results_2026-11-09.md), [full v2 and two-arm union](../../review/ep_bva_dt_v2_union_results_2026-11-10.md).

Full v2:157eligible tasks/1454PUTs;EP+BVA81PUTs/32tasks,DT96/34;union113/41. Union uses40inputs/task vs20per arm.314responses/316attempts/2unknown usage,1,328,124known tokens. Cross-run v1-v2 comparisons are descriptive; prompt/examples/visibility were not isolated. No new workload is needed to use the saved reports.

Followup scheduling uses `not_before_utc` AND verified predecessor completion. During preparation/waiting no model/tokenizer/native calls occur. Config/cohort/code/example assets and private route are snapshotted. Failed predecessor blocks the followup; no automatic experiment expansion.

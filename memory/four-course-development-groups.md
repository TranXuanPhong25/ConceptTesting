---
name: four-course-development-groups
description: User develops boundary/equivalence/C1/def-use separately;164tasks reviewed,6PUT smoke per group, outcome-blind source/base selection
metadata:
  type: project
---

User2026-11-03 requests developing concepts along four test_slides methods:
boundary, equivalence partitioning, statement coverage via CFG, and def-use/data
flow. Read all164task specifications, assign development priorities, improve each
small group before integrating. Do not rerun all164for every local change.

Implemented offline `final/development_groups.py` with manual164row review and
reports/manifests in `final/review/development_groups/`. Primary counts47boundary,
47equivalence,31statement,39def_use; multiple secondary labels allowed. Source/base
gates leave44/46/15/35ready primary task groups, respectively. Static library graph
errors264of1465base-pass PUTs are explicit, not fabricated coverage. Statement uses
coverage.py executable-line proxy; DU uses LAST_WRITE static may-flow, never claims
that dynamic def-clear paths were covered just because both endpoints executed.

Each group has6source-selected PUTs on6tasks for smoke; dev≤12(11forstatement),
check4task-disjoint from all development groups. These are development checks,
not fresh heldout. Preserve original program IDs/source/base results in subset
cohorts. Exported representative cohorts require target_programs1 and selecting
only manifest task IDs with the pipeline API. Current CLI defaults164/10 and must
not be used with only --cohort for these exports. No four-method generators are
implemented by this selection utility; mixed classical/V11 on a subset does not
establish method-specific efficacy.

9engineering checks and independent read-only review pass.24smokePUTs materialized
under `final/out/development_groups/{group}/smoke/`; no model/PUT execution or
reference/plus outcomes used in selection. Existing full concept-inputs service
36821 remains active;105source hashes unchanged. No commit/push. Next work is
criterion-specific concept providers with fixed generator/oracle/budget, then
deduplicated combined evaluation; do not sum detection counts across groups.

**Why:** local development on the fullcohort is too slow and mixed concepts make
mechanism failures hard to diagnose. Prior v7/v11/classical already contain these
criteria; grouping is a development strategy, not a novel testing method claim.

**How to apply:** use README/REPORT/task_review.tsv in the review folder; select
the direction's smoke first, then development/check, before a combined/full run.
Maintain unsupported/invalid/infeasible/unknown outcomes and the plain baseline.

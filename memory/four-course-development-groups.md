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

2026-11-05 user corrects the assistant's smoke-only plain+BVA run and points to
final/development_groups.py. Do not present the6PUTsmoke as the complete grouped
dataset. Exported actual boundary/tierall using the script:44ready tasks of47primary,
1representativePUT/task (83/PUT2,103/PUT1,othersPUT0);65/127/163not ready.
Outputcohort final/out/development_groups/boundary/all. Newrun
final/out/boundary_all_plain_bva_20261105 imports6matching generation checkpoints/
16requests,122files;38fresh tasks remain. Source/settings/model unchanged;reuse
shared native cache post-freeze. Review:final/review/boundary_all_run_2026-11-05.md.
Endpointmodels404;supervisor168654waiting/polling60s,0freshcompletions/nocontroller.
User asked forcurrentendpoint. This is scope correction,not efficacy-driven expansion.

2026-11-05 user supplies refreshed endpoint,explicitly requests background in
boundarygroup. Metadataqwen27/context8192/tokenizer13verified;68sourcehashesmatch.
Supervisor168654launched detachedcontroller170173,actualfreshHumanEval2/plain
attemptstarted observed. Statusrunning;6inputfilesareimported,38newtasksremain
atlaunch. Keep cachedcohort/config/inputs and20mkeepalive;do not duplicate launch.

2026-11-05 TERMINAL COMPLETEboundary/all44supersedesrunning:44input/results,
controller170173exit0. Plain595validinputs/3detectedPUTs;BVA121/3. Both44/122,
plainonly97,BVAonly140;union4.114responses(16imported+98fresh),0unknown;
154417freshknown tokens+32785imported=187202. Nativecache486hits/2692executions
of3178records;44freeze/68sourcehashesverified. Development,unequalcalls/yields,
no efficacygainclaim. See final/review/boundary_all_run_2026-11-05.md.

2026-11-05 correctedoracle supersedes rawdetectioninterpretation:exact same44
taskinputs rescored with HumanEval+v0.1.10→plain0/BVA0detected,595/121validinputs
unchanged.0LLMcalls,all1336source-run artifacts unchanged. User now requests BVA
improvement proposal;no expansion/newgeneration. See [[reference-oracle-bugs]].

2026-11-05 repaired-methodrun now authorized/running on sameboundary/all44,
not smoke or other groups. Outputboundary_all_plain_bva_compiled_20261105;
controller199379,77source/datahashes,newgenerationall44,namedplain/compiledBVA,
correctedoracle/sharedcache. Firsttask0plainresponse received,BVAselectionstarted;
no scored outcomesyet. See [[boundary-test-applicability]].

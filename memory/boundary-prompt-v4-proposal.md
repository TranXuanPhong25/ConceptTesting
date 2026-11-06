---
name: boundary-prompt-v4-proposal
description: BVA v4→protocol5 known-bug10 diagnostic complete;4vs1 tasks,64inputs/16calls, post-hoc and not efficacy
metadata:
  type: project
---

2026-11-05 user asked for a Boundary prompt set derived from their BVA note and test_slides/03, compared with the
current module prompt. Proposal only: final/review/boundary_prompt_v4_proposal_2026-11-05.md. prompts.py unchanged, 0 LLM calls.

Saved compiled run evidence (pre-v3 prompt): 7/18 no_applicable abstentions treat preconditions as non-boundaries
(122/159 quote the prompt sentence); 7/8 behavior boundaries lack a side; task140 context lost because the model copied
the placeholder key "parameter". V4: 5-step worksheet (order, transitions spec/code/edge, align, RIP, select).

**Why:** the current prompt mostly prohibits and carries cohort-derived task sentences (99/124/140/21/146).
**How to apply:** before running, keep new fields in BoundarySelection.validate (they are dropped today), bump protocol,
use a fresh output dir, compare with plain and a placebo at matched budget. Never few-shot tasks 44/97/122/140 (in the
cohort, and reference bugs rather than PUT bugs). Related: [[boundary-test-applicability]], [[v34-ftplacebo]].

2026-11-05 update: user said try; v4 applied in final/src/modular/boundary_value_analysis (schema 4), 219 tests pass then.
Smoke final/out/boundary_smoke_prompt_v4_20261105: 6/6, 8 calls, 12 inputs, detected 99 PUT0. Tasks 81/120 lost to
invalid_constraint (v4 example dropped constraint object); prompt fixed afterwards, smoke NOT rerun.
User then asked for 10 tasks with certain boundary bugs: final/review/boundary_known_bug_tasks_2026-11-05.{md,json}:
2,11,16,23,72,76,99,124,140,157, each replayed twice on corrected references, nominal passes. Outcome-selected diagnostic only;
PUT ids differ from cohort representatives; 16/23 need a char-code characteristic.

2026-11-05 known_bug_10 diagnostic (constraint fix included): final/out/boundary_known_bug10_prompt_v4_20261105, 14 calls,
10 inputs, detected only 124. Lost at selection: 2/11/16/23/157 abstain with "no spec threshold" despite origin edge/code;
76 picked n<=1 not x==0; 99 truncated at selection_tokens 2048. Lost at context: 72 (no negative values), 140 (not all-space).
Not a detection rate. At diagnostic completion, no tuning or rerun had been done.

2026-11-05 user then requested the diagnosed fixes. Protocol5 repair implemented
in the existing BVA module, documented in final/src/modular/boundary_value_analysis/README.md
and dated CHANGELOG/PREREG entries.223 modular engineering tests pass. No new model,
diagnostic or benchmark run; efficacy remains untested. Future generation requires
fresh artifacts; prior known-bug10 results remain the historical diagnostic.

2026-11-05 user explicitly requests rerun. Independent Codex review found two
remaining spec-threshold/rule-difference requirements in template metadata and
context prompt; both corrected before inference,223tests pass. Live exact-model
metadata and all10selection prompt context checks pass. Detached diagnostic
launched in final/out/boundary_known_bug10_prompt_v5_20261105, PID299674;
max20logical calls, same10outcome-selectedPUTs and corrected-reference pipeline.
Inspect status.json before any launch/resume; never duplicate. Snapshot records
source/old-output hashes and readiness. Manual user-requested1token ping received
separately from task accounting. Endpoint config remains outside repo.

2026-11-05 protocol5 rerun COMPLETE10/10, superseding launch.16responses/0unknown,
64valid inputs, bug tasks76/99/124/140vs v4only124. Post-hoc diagnostic, not a
detection rate. Report:final/review/boundary_prompt_v5_diagnostic_2026-11-05.md.
72still lacks negatives;2/11abstain;16wrong char-code→length binding then truncated
context;23unsupported;157wrong edge. All291prior files and10input-freeze hashes
verified; native disagreements stable in both repeats. Another session edited
runtime/model.py and modular/pipeline.py after launch/import; all BVA/evaluation
sources unchanged. Current-tree full replay correctly fails the source guard;
exact launch controller sources recovered/hash-checked as .py.txt evidence.
See postrun_audit.json. No active diagnostic controller or authorized expansion.

2026-11-05 userrequested six-failure trace complete, no new model/PUT/reference
execution. Exact contexts/constructor transformations and native outcome paths:
final/review/boundary_prompt_v5_failure_trace_2026-11-05.{md,json}. Pure constructor
replay72/157matches saved inputs. Adds semantic false-mismatch diagnosis for72/157,
PUT/spec confusion23and observed-int neighborhood restriction157despite float
contract. Consult the trace before proposing fixes; no implementation changes.

2026-11-06 user approves testing prompt compression. Compact selection only,
5908→3347characters; context/output JSON example and3task-data objects match
v5exactly.234modular tests/prelaunch review pass. Protocol6. Runtime transport
changed since v5, so prospective PREREG amendment adds3fresh long-selection
controls interleaved with3short selections; up to3short contexts afterwards,
max9logical calls. Same23/72/157PUTs, no new hints/menu changes. Detached
runnerPID332310 in final/out/boundary_compact_selection3_20261106; inspect
diagnostic_status.json before any action, never duplicate. Primary semantic
comparison, not efficacy or pure causal length isolation. Endpoint outside repo.

2026-11-06 compact diagnostic COMPLETE, superseding launch.8responses/0unknown,
3fresh long controls exactly match v5texts. Short23recognizes byte/character
distinction but context yields only duplicates;72still false operator mismatch;
157same semantic error plus invalid origin=contract. Short pipeline11valid/0bug.
Report:final/review/boundary_compact_selection_2026-11-06.md. Full read-only replay
matches;76source/data+312prior files unchanged. Candidate prompt retained for
review, no retune/expansion; no general efficacy or pure-length conclusion.

2026-11-06 user selects v5default and explicitly requests commit/push to main,
then trials of the proposed semantic-grounding improvements. Restored exact
v5selection/context bytes and schema5; compact instructions archived for review.
Default remains diagnostic evidence, not globally best. Grounding trials follow
as separately recorded experimental work; preserve prior outputs and other
sessions' uncommitted files.

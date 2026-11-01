---
name: final-humaneval-pipeline
description: Frozen cohort164/1634PUT/1465basepass; streaming recovery ready42tests, scheduler115270 retry13:38:15Vietnam
metadata:
  type: project
---

2026-11-01 user-requested modular refactor COMPLETE in final/modular/: separate
arm modules/classes, PipelineStage.run(TaskContext), per-stage classes, shared
ArtifactStore/ModelCalls and BenchmarkPipeline.insert_stage().15engineeringchecks
pass, independent review cleared;full164cachedtask replay/2296stageevents matches
inputs/oracle/outcomes/FULLsummary including costs/diagnostics/pvalues.23original
source/cohort/result hashes unchanged,0newAPI/nativebenchmark executions. Default
CLI replay is read-only;witness-only run needs no model;writable stage events saved.
Docs final/modular/README.md and VALIDATION.md. Original experiment remains complete,
no jobs running and newpipeline/refactor/memory still uncommitted per user request.

2026-11-01 TERMINAL COMPLETE supersedes all running/waiting/stop notices: scheduled
scheduler8204/controller8532 both exited successfully.164input/scored taskfiles,
157eligible tasks(7explicit skips),1634generated PUTs/1465basepasses/1454evaluated.
Raw reference-disagreement PUT counts:plain78,classical74,contrastive78,placebo86,
toolinput140,witness53. PRIMARY matched-valid-budget classical/plain macro task
fractions.04933/.05067,p=.7483;3–3tasks withmore detections. No demonstrated concept
gain. Raw toolinput140 usesmore validinputs,not a matched superiority claim.
83primarypairs zero validbudget;4023domain/reference rejects,258unsupportedgraphs
limit interpretation.785received testerresponses,8unknown attempts;writer434/
1unknown;observer21received/15unknown separate. Result164rows/armtotals and input
freeze hash independently checked. Report at recovery/REPORT.md and summary.json.
No new inference,rerun,commit or push;pipeline remains uncommitted per user request.

2026-11-01 user explicitly schedules resume15minutes later, superseding stop:
scheduler8204 verified alive,waiting_retry_deadline until02:53:44UTC/09:53:44Vietnam
on01Nov. Source/review hashes unchanged;private endpoint config reconstructed
outside repo. Controller remains user_stopped untildeadline,then metadata gate
and automatic resume161cachedinputtasks/777responses. Retry interrupted161/162
only within persistent completion caps;history preserved. No new completion before
deadline. Inspect recovery_schedule/status.json;do not launch duplicate scheduler.

2026-11-01 01:12Vietnam USER STOPPED: user explicitly said stop. Sent SIGTERM to
verified scheduler14844/controller14898; both exited. Both lifecycle files marked
user_stopped; no automatic resume. Saved161inputtasks/777responses,0scored; active
task161/contrastive and162/plain request records retained without responses (usage
unknown). Stop audit under recovery/stop_audit/20261031T181258Z/. All cohort,
inputs and responses preserved. Resume ONLY on explicit user request; never replay
these unknown attempts silently. Older running notices below superseded.

Latest user-authorized resume after grouped commits: private /tmp endpoint/deadline
files had disappeared; rebuilt them from user-supplied endpoint, never stored URL
in repo. Metadata confirms qwen3.5-27b-awq/context8192; all source/review hashes and
Python3.11.14 match. Archived1809checkpoint hashes. Scheduler14844/controller14898
alive; reuses107inputtasks/526responses, frozen PUT cohort unchanged. Actual new
task108/plain completion received (508output/2870total tokens, usage complete),
responsecount527; task107/classical in flight. No duplicate jobs or source changes.
This new pipeline and its memory remain uncommitted per user's explicit request.

2026-10-31 12:17UTC continuation/status: endpoint recovered; scheduler115270
automatically resumed controller121309. Both alive; inputs99/164tasks,487responses,
0scored. Task99/contrastive and100/plain in flight, first attempts. Former93/94
stopping points cleared. User says continue; no duplicate process launched and
no source/cohort changes. Older waiting-for-endpoint notices superseded.

2026-10-31 10:59UTC check: scheduler115270 alive WAITING_FOR_ENDPOINT(models404).
Controller115608 exited on tokenizer404, before sending another completion.
Input generation93/164tasks,458responses,0scored. Task93/contrastive and94/classical
each archived one interrupted stream; all partial outputs excluded. Original16
and recovered41 unknowns also retained. Scheduler polls metadata only and will
resume automatically when expected endpoint/model returns; do not launch duplicate.
Earlier active-generating notices below superseded. Cached cohort unchanged.

2026-10-31 09:34UTC check: recovery controller115608/scheduler115270 alive;
input generation81/164tasks,395receivedresponses,0scored. Tasks81/82 plain calls
inflight. One new task41/placebo TimeoutError with1215partialchars was archived;
automatic retry succeeded and task41 completed. Partial output was not a test suite.
Total unreceived history:legacytask16 + recoveredtask41, plus2currentinflight.
Earlier progress snapshots below are superseded; no new launch/repair in this check.

2026-10-31 07:04UTC check: scheduled recovery successfully launched controller
115608; scheduler115270 and controller both alive. Input generation26/164 tasks,
131received responses; task16 completed and passed the former stopping point.
Two requests currently in flight(task26/classical,task27/plain), no new unknown
failure; original legacy tester unknown is archived/accounted.0scored tasks yet;
cohort remains frozen164tasks/1634PUTs/1465basepasses. Main lifecycle now at
final/out/concept_reference_v1_recovery/status.json. Older waiting notices superseded.

2026-10-31 transport recovery supersedes stopped/audit notices: user asks fix/resume,
then explicitly '20p nữa thử lại'. Current endpoint models/tokenizer404; no new
completion sent. New isolated final/experiments/concept_reference_v1_recovery
uses streamed responses, structured errors, safe read retries and legacy-inclusive
3totalcompletion-attempt cap. Original source/output/cohort unchanged. Imported
331files/18inputtasks/91responses;all92cachedrequestrecords match reconstructed
prompts/seeds/caps.42engineering tests pass;independent review cleared.

SchedulerPID115270 loaded final code and waits until2026-10-31T06:38:15.892378UTC
(13:38:15Vietnam). It checks27reviewed source/data hashes and expected model/context
before launching. While endpoint offline only metadata polling60s; auto restart
only safe read failures, never reset completion cap. New lifecycle:
final/out/concept_reference_v1_recovery_schedule/status.json; output continuation:
final/out/concept_reference_v1_recovery/. Private endpoint env file outside repo.
At release scheduler alive/waiting_retry_deadline, no controller started yet. Check
live status rather than assuming a launch/completion; do not duplicate scheduler.

2026-10-31 readability-audit status supersedes running notices: controller107832
has exited/interrupted RuntimeError. Cohort is FROZEN,164tasks/1634PUTs/1465base
passes.18input task files saved (main progress17 + drained completion),0scored.
Tester task16/classical has one unknown-response ModelError slot; original writer
unknown remains historical separately. No retry or source refactor performed in
the user's readability-review turn. Audit is final/review/READABILITY.md; code and
checkpoints untouched. User prefers explicit naming; see [[code-readability]].

2026-10-31 retry supersedes stopped notice: user explicitly requested retry with
same endpoint/model. Metadata200/samemodel8192; frozen source hashes unchanged.
Archived the task118/programs_00 unknown request in sibling
`programs_00_unknown_attempt_0000` (still counted as one historical unknown).
Verified all1603 cached cohort/base/response files unchanged; archived old logs/
status and authorization under run `resume_audit/20261031T021800Z/`.
Detached controller107832 launched with original config; reuses all118 cached
tasks/1175PUTs/1086basepasses. New task119 response received; task118 retry initially
in flight, then successfully received/saved a response after129.7s (1643known
tokens). Historical original1unknown remains separately counted. Inspect live
status; do not duplicate launch. No tester/scoring yet.

2026-10-31 latest status check: controller93111 is NOT RUNNING; status interrupted
RuntimeError after a ModelError on task118/programs_00 (one request without saved
response, unknown usage). Durable cache includes118tasks/1175programs/1086basepasses;
controller's progress117 excludes an additional task drained during shutdown.
No tester calls/input generation/scoring yet. Current supplied endpoint GET/models
returns200 with the same model; do not mistake endpoint liveness for a running job.
Earlier launch/running observations below are superseded. Preserve all responses;
do not blindly replay the unknown invocation or regenerate cached PUTs.

2026-10-30 latest (Codex): user clarified that this is a concept-utility benchmark,
using boundary/equivalence/CFG/def-use analysis of base tests+PUTs, with reference
program as oracle. Generate the PUT cohort **once**, reuse for all later concept
experiments; no LLM expected-output oracle. User requests research beyond v7/v11,
prefer libraries, test endpoint first, and do not stop before actual runnable work.

User supplied qwen3.5-27b-awq; metadata8192 and real33-token probe passed. Never
persist its endpoint URL in repo/memory/logs. Runtime configuration is outside repo.
New separate implementation `final/experiments/concept_reference_v1/` uses original
python-graphs, coverage.py, NetworkX, Hypothesis and EvalPlus contracts/tolerances.
Primary classical/plain, secondary cross-PUT contrast, placebo/toolinput/witness
controls. 27checks+164/164tracedcanonical pass, independent review cleared launch.
Full164 detached controller PID93111 launched, initially building cohort at
`final/out/cohorts/qwen35_27b_humaneval164/`; lifecycle at
`final/out/concept_reference_v1/status.json`. Inspect current PID/status, do not
duplicate. No efficacy result yet; launch is not completion. Old waiting notices
below are superseded by this paragraph. Actual live model→input→reference→PUT
readiness also PASS on separate engineering fixture:3validinputs/error detected,
702tokens;735known diagnostic tokens including transport probe,not benchmark.
First observed cohortprogress3tasks/30programs/27basepasses,0unknown. These counts
are observations,not terminal results;inspect live status. No commit/push requested.

2026-10-30 earlier (Codex): user requested a new root `final/` folder and replaceable
`CoreModel`: generate 10 distinct programs per HumanEval task, retain base-test
passes, one additional model call for a shared new-test suite, measure failures.
User explicitly selected **all 164 tasks**, and **will provide model/endpoint**;
do not silently select another backend or start with historical endpoints.

Implementation/review complete; 17 engineering checks and 164/164 canonical-only
base checks pass. No real LLM calls or generated-program benchmark results yet.
Use `final/README.md`, `final/PREREG.md`, and `final/validation/REPORT.md` as the
authoritative protocol/evidence. Python 3.11.14 from `CoverUp_concept/.venv/bin/python`.

**Why:** this is the user's simplified independent pipeline, not an extension of
the older concept/retrieval arms. Keep earlier pipelines/source untouched.
**How to apply:** wait for the supplied backend, set configuration through env
without persisting URL/keys, then run all 164 with frozen manifest/checkpoints.
Report incremental test failures, not recall or proven spec bugs. No commit/push
was requested for this root-folder work.

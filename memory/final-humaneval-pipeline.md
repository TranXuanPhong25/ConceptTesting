---
name: final-humaneval-pipeline
description: Full V11 stopped288/1634; new v11_concept arm uses V11 concepts with the modern inputs-only generator; uncommitted for review
metadata:
  type: project
---

2026-11-04 16:38Vietnam read-only check:83538stillactive/task139. PUT5 finished
with preparation_failed/RuntimeError/cards[] after~60min; do not treat as successful
concept extraction. NowPUT6/v11_facts nativePython84585~99.8%CPU/~54min since15:44.
139inputs/268testerresponses/0scored unchanged;4172conceptresponses total(+5since
15:23),latest15:44:02;keepalive16:23:33received. No fix/restart/settings change.

2026-11-04 15:23Vietnam read-only check: service83538active but still task139,
PUTindex5/v11_facts/fact_worker since14:43:46. Native sandbox Python83762 consumes
99.8%CPU/~39m40CPUtime;worker progress heartbeat current,idle0s,not waiting on API.
Only5newconceptresponses since resume(latest14:43:45);keepalive15:03received.
139inputrecords/268testerresponses/0scored unchanged; no terminal result/no repair
or restart performed. CPU work advancing does not establish useful task progress.

2026-11-04 user supplies refreshed private endpoint; resume authorized. Metadata
expectedqwen27/context8192 and tokenizer13 verified. All105sourcehashes unchanged;
69531artifacthashes snapshotted under resume_audit/20261104T074310Z. Existing
concept-inputs service restarted14:43:25Vietnam,PID83538/statusrunning, resumed
HumanEval139 concept extraction; actual fresh received conceptresponse observed.
139inputtaskrecords/268testerresponses at resume. Same arms/settings/cohort and
20mkeepalive;no PUTregeneration. FullV11 remains stopped. Supersedes failed notice
below;inspect live status before further action. Endpoint stored only outside repo.

2026-11-04 status check (Codex): no local experiment process running. Concept-inputs
service failed/exited1 at10:40:04Vietnam;MainPID0,status interrupted. Tokenize
HTTP404/TransportError during HumanEval139 concept extraction; completion_started
false for this failed operation. FullV11 service inactive. No restart or endpoint
calls during this check; prior active notices superseded. Live status and events:
final/out/v11_concept_inputs/{status.json,stage_events.jsonl}.

2026-11-04 TERMINAL COMPLETE supersedes all running/offline notices: concept-inputs
controller95119exited0,serviceinactive.164input/result records,156eligible tasks,
8explicit skips;1437evaluatedbase-passPUTs after17userresourceexclusions (original
sourcecohort1634/1465;11more basepasses in original shortfall tasks not evaluated).
Raw own-run detections plain72/18tasks vs v11_concept90/24tasks;validinputs1530/
1528. Primarytask-matched validbudget macro.05211895vs.05259972,p=.970303,
taskwins5–5;85of156pairszero validbudget. No demonstrated matched conceptgain.
312testergenresponses;conceptprep1437records(273imported/1164computed),19failures,
2342cards,4984received/4987prep invocations,2,085,985knownpreptokens;historical
mining1192requestkeys referenced separately. These are terminal counts,not old
completedv1'splain78. Summary totals,all164inputfreezehashes,1437denominator,and
excludedPUTabsencefromevaluation verifiedread-only. REPORT.md and
modular_summary.json in final/out/v11_concept_inputs;no newexecution/commit/push.

2026-11-04 user requests continue: prior endpointB models200/tokenizerOK,
expectedqwen27/context8192;other prior endpoint still404.107reviewed source/plan
hashes verified,1693completed primaryartifacts snapshotted. Service restarted
PID95119with --v11-resource-exclusions flag;fresh task142concept-extraction started
verified against newstatus/filemtime (oldfailed event must not count asresume).
Resumes142inputrecords;17user-authorized PUTexclusions active;expected1437evaluated.
FullV11 remains stopped;no regeneration/sourcechange/retrycapreset or commit.
This supersedes endpoint-offline notices below;inspectlivefilesforprogress.

2026-11-04 latest user explicitly authorizes excluding likely expensive remaining
PUTs from BOTH concept preparation and evaluation (not preparation-only skips).
Reviewed181unfinished base-pass sources;exclude17:144/9;147/1,2,3,5,6,7,9;
150/0,2,3,4,6,7,8,9;160/6. Source/spec/cohort-bound plan in
final/review/resource_risk/resource_exclusions.json and run output. OptionalCLI
--v11-resource-exclusions filters context before mining,sharedBOTH-arm prompts,
witnesssampling,evaluation;160explicitall-base-pass-excludedskip. Original frozen
cohort unchanged;expected evaluated1454→1437. Existing completedfailedrecords
notreclassified.56checks+independentreviewpass;PREREGamendmentrecorded.
Originalmanifest+6oldsourcefiles+19514cachedartifacthashes archived/preserved in
resume_audit/resource_exclusions_20261104T124232Z;runmanifest amended withplan,
source/config changes only.17exclusionmarkers appliedoffline,no model/PUTexec.
Service flagconfigured but serviceFAILED/MainPID0 aftertokenize404;bothprevious
endpointsmodels404. Readinessready_waiting_endpoint;cached142inputrecords/
1273conceptrecords atstartofaudit. Resume only whenendpointworking,withnewflag;
no newversionfolder orcommit/push. Updatedcode stayslocal forreview.

2026-11-04 diagnosis of task139(special_factorial) slowness: saved mining strategy
is st.tuples(st.integers(min_value=1)),no upper bound. Original facts fuzz400inputs;
completed task139caches contain huge n (e.g.3762591980434786304). PUT9computes list
of math.factorial(i) for i=1..n then product. Per-call trace has20s wall safety net,
coverage1s,outerfacts3600s; many huge/slow inputs multiply cost.7of9base-pass PUTs
in task139now preparation_failed after3600s each;other2facts finished554.1s/135.2s.
Worker had realCPUprogress before its timeout,so evidence supports expensive
unbounded fuzzing rather than the earlier zeroCPUcoverage deadlock. No stack could
be captured once worker exited;do not claim exact inner loop stack measured.
Service83538subsequentlyfailed tokenize404 again;verify checkpoint counts from
actual files before resume. No runtime/method sourcechange.

2026-11-03 latest user instruction authorizes splitting current changes into
commits on main, superseding earlier leave-uncommitted notices for these changes.
Groups: V11runtime/adapters, modernconceptarm, fourcourse development subsets,
PUTqualityaudit,sharedmemory.49engineeringchecks passed before commits;105active
sourcehashes unchanged. Commits a790f504/runtime,19c786cd/conceptarm,40c31400/
developmentgroups,15f3a48d/PUTaudit plus sharedmemory commit. No push requested. Outputs/checkpoints/workerenvs and
detaileddevelopmentinventory stay local/ignored;source105hashesverifiedunchanged.

2026-11-03 latest: user says keep current run/settings and endpoint alive again.
Configured endpoint models404, but other previously supplied endpoint metadata200,
expectedqwen27/context8192/tokenizer13 verified; private configuration updated only
outside repo. Source105hashes unchanged;3122completed caches snapshotted. Service
concepttester-v11-concept-inputs restarted PID60795, reached task83concept extraction
using83inputtaskrecords/162testerresponses/772conceptcheckpoints. FullV11 stays
stopped; no generator/protocol changes or PUT regeneration. This supersedes prior
interrupted/36821active notices; check live files for progress.

2026-11-03 user supplies refreshed private endpoint and authorizes resume.
Concept-inputs service restarted controller36821 after models200/expectedqwen27/
context8192 and105sourcehashes verified. Reached HumanEval60 concept extraction
again;747saved inputs/responses/concept checkpoints snapshotted in resume_audit.
Previous stop was tokenize404 before completion. Resume frozen60inputtasks/
118testerresponses/569conceptrecords; no regeneration or retry-cap reset. Output
final/out/v11_concept_inputs; inspect live progress. FullV11 stays stopped.

2026-11-02 user requests redundant-code removal: deleted obsolete final/v11_clean/
source copy only. Keep final/v11_clean_runtimefix/ adapters required by active
modular concept arm; original V11/history and ALL outputs/checkpoints preserved.
Active run manifest source hashes verified unchanged; service15805 stays active.
No commit/push.

2026-11-02 user explicitly authorizes RUN with refreshed private endpoint. Metadata
expectedqwen27/context8192 and real17tokenprobe passed;26engineeringchecks and
independent read-only review cleared single launch. New service
concepttester-v11-concept-inputs.service ACTIVE controller15805; output
final/out/v11_concept_inputs. Arms plain+v11_concept ONLY, modern one-call/task
inputs-only generator; no fullV11 restart. First task imported9conceptcheckpoints
and entered input_generation; verify actual response progress before reporting
completion. KeepAlive20min separate, bounded transport retries, lifecycle status,
source/config manifest and stage events. No automatic terminal-failure restart
configured; preserve caches and inspect errors before retry. FullV11 remains
user_stopped. This launch supersedes prior awaiting-review/no-launch notices.
No source folder fork, commit or push. Endpoint stays outside repository.

2026-11-02 latest user clarification: new versions/arms modify existing source,
without copying another version folder; leave changes uncommitted for user review.
Requested arm is ONLY V11 concept extraction with the modern test generator.
Implemented in final/modular/: V11ConceptArm, V11ConceptStage, generic arm hooks
for preparation/guidance/reporting, and separate preparation-cost reporting. Actual
V11 mining/facts/top3/spec fallback reused read-only; no V11 hybrid/assertion/LLM
expected-output generation. Modern common prompt/one-call inputs-only parser,
reference oracle and shared-suite/all-PUT evaluation unchanged. Aggregate at most
4cards from visible PUTs, rank-first round-robin, with AST-translated locations.
Imports validate method source/model/tools/raw PUT/view/spec and never read old
result/oracle files. Missing cache mines only concepts; infrastructure/model-cache
errors propagate. Existing modern shortfall policy means157eligible/1454PUTs,
not full-V11's1465. Cache-only validation imported525cards/264PUTs/28tasks, no
inference/outcome execution. Historical164task/2296event replay still matches.
26engineering checks pass; documented in final/modular/VALIDATION.md. No new benchmark run,
automatic launch, commit or push before user review.

Full V11 STOPPED by explicit user reply:288durable results(271complete,
16base_rejected,1preparation failure). concepttester-v11-clean-runtimefix.service
inactive/MainPID0, STOP marker and both statuses user_stopped; no automatic resume.
4533completed result/response/concept hashes verified unchanged in
final/out/v11_clean_runtimefix/stop_audit/20261101T165215Z/. Preserve all partial
request history as well; new arm's optional source cache reads this stopped run.
This supersedes every running/active notice below.

Runtimefix later status: controller62479/service62463 alive,241/1634durable cases
(226complete,14base_rejected,1preparation_or_execution_failed).3266responses saved,
heartbeat8s old,NRestarts0;cases240/242inV11hybrid,factscomplete. Case197(HumanEval19/
program7,sort_numbers) has nativefacts worker_errorNameError;explicitzero-evidence
case,not a runstop. No newcoverage deadlock visible. Preliminaryrawconcept24/plain17/
placebo25/tool25/witness4atlastsummary;no terminal/matched conclusion or methodchange.

Runtimefix live verification: checkpoint advanced155→156/1634;case156finished FULL
pipeline including reference evaluation. Case151facts also finished and is inhybrid.
Controller62479/service62463active;2149responses saved atcheck. Old4439artifacts
preserved. This confirms progress beyond the observed collector deadlock, not just
aliveprocess/heartbeat. No efficacy conclusion from partial run.

V11 runtimefix ACTIVE supersedes old 'normalCPU' report: user correctly noticed
155case count stopped. Both workers151/156were DEADLOCKED at coverage.collector
_clear_data→flush_data/get_data,0CPUdelta,singlethreadfutex,despiteparentheartbeat.
Oldservice stopped+disabled. New isolated final/v11_clean_runtimefix supported
COVERAGE_CORE=pytrace with same7.16.2/tools/kernels; originalsource unchanged.
14engineeringtests+independentreviewpass;4439completedartifacthashes imported;
freshscratch native retry once on120sCPUidle,oneoverallwallbudget; recurringidle
or deadlineafteridle raises infrastructure WorkerStalled,nevermethodzero.
Newservice concepttester-v11-clean-runtimefix.service supervisor62463/controller
62479alive,guard72files. Formerstuck151/156both consumed~40CPUseconds/40wallsecs,
idle0s atcheck;stillfactsnotyetnewcompletedcase. Activeout final/out/v11_clean_runtimefix,
schedule final/out/v11_clean_runtimefix_schedule;inspect worker_progress CPU/idle,
not justprocessalive. No newmodelrequests during initialresumedCPUwork;cohort,
savedmodelresponses and completedresults preserved. No commit/push.

V11 clean progress check ~5h after launch: service/supervisor44127/controller44418
alive,heartbeat16s old,NRestarts0.155/1634case results:145complete,10base_rejected,
0preparation/runtime failures.2142receivedresponses,3historicalunreceivedattempts;
both activecases151/156currentlyoriginalCPUfacts. Preliminary raw detections at
lastsummary:concept6/plain3/placebo7/tool8/witness2;not terminal/matched conclusion.
No launch/change/newanalysis in this status turn;keep fullrun and checkpoints.

V11 clean live end-to-end follow-up: first2PUTcases0/1 completed all B5/facts/
hybrid-controls/reference-on-raw-source evaluation; cases2/3nowinhybrid.28actual
responses saved atcheck,controller44418/service44127alive. No interpretation of
early efficacy, no extra sampling or source changes. Sourceguard71hashes stillmatch.

2026-11-01 V11 CLEAN ACTUALLY RUNNING after user25min deadline: supervisor44127
(systemd concepttester-v11-clean.service) launched controller44418 after07:05:32UTC.
Endpoint exact qwen3.5-27b-awq/context8192. First2cases(0,1) completed B5/domain
mining and original native facts, now V11 hybrid generation;14realresponses saved,
no case result/efficacy conclusion yet.10tests/static1634views/review/hashguard71
remain valid. Per-class files mining/facts/round_one/hybrid;stage_factories allows
extension. Monitoring30s and keepalive20min separate;same frozen cohort,no regen.
Check v11_clean/status.json +v11_clean_schedule/heartbeat.json before action.

2026-11-01 user authorizes clean V11 arm/stages + full existingcohort run and
autonomous progresschecks/fixes; endpoint said available25minlater. New isolated
final/v11_clean uses originalV11 B5/domain/facts/spec/hybrid kernels/prompts,
K1/qwen27/canonical-reference/perPUTalias adaptations registered. Controls matched
plain/placebohybrids +toolinput/witness; own-PUT suites only,task-total valid-budget
diagnostic. Manifest includesall1634/1465basepass,169base rejectslogged;no regen.
10engineering tests/review PASS;1634views compile/body-preserved;original51V11
files unchanged. Earliest launch07:05:32UTC/14:05:32Vietnam01Nov;readyguard71files.
Systemd user service concepttester-v11-clean.service active supervisor44127,
waitingdeadline atrelease; no completion yet. Progress30s,20minrecordedkeepalive,
transientboundedrecovery,terminalcaps/source-driftneedreview. Endpointprivateconfig
outside repo; userstop requires STOP marker in v11_clean_schedule and service stop.
Inspect final/out/v11_clean_schedule/{status,heartbeat}.json and v11_clean/status;
do not duplicate launch. Newpipeline remainslocal/uncommitted;no efficacyresultyet.

2026-11-01 saved-data PUT quality audit (user asks whether old LineFacts PUTs are
better): vendor151files,method139cachedbasepasses/138plus-failing(task66zero);
v7bundle133=113dev+20pilot,all133source matchvendor. New1465basepasses/159tasks,
1454evaluated;all-arm reference-disagreement union171PUTs/40tasks is lowerbound,
not total defect rate. ASTcanonical matches21modules/22entryfunctions,not evidence
of mass identical copying. Median branches3both. Olddocmismatch69/108/116/131/152,
task50specambiguity,oldpoolheavilyuseddevelopment. Recommend oldcuratedpool as
development benchmark for targeted bugfinding,newpool supplementary;no change
to completedrun,no newcalls/nativeexec. Before integration revalidate qualification
and separate frozenonePUT/taskcohort/settings target1;no adapter/run implemented.
Report final/review/put_quality/REPORT.md + audit.py/SUMMARY.json.83zero-valid-budget
pairs/258graphfailures in currentrun remain pipeline limitations independent ofpool.

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

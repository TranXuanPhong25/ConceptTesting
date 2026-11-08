---
name: boundary-input-generation-priorwork
description: Input buckets may be defined from impl/spec before base membership filtering; LISP/DSpec2Test are direct prior work, research-only
metadata:
  type: reference
---

TERMINAL2026-11-08 grounded continuation COMPLETE:all4candidates44taskrecords,
allimmutable replayPASS;Prefect98959f77Completed. NovelvalidinputsLISP30,
CrossHair8,DSpec32,ISLa9;detectedPUTs0all. Fullrunresponses197/0/20/19,
tokens254167/0/26033/35873(total236responses316073known tokens,probeusage separate).
LISP/CrossHair reusedunchanged;DSpec/ISLa finishednew continuation183913.
Supported scopes remainlimited:DSpec20unsupportedformaltype+10unsupportedcontract,
ISLa26unsupportedinterface+10unsupportedcontract;LISP18invalid_candidate_data.
Do not confuse44processed tasks with44generatedinputtasks;0detectionis not a
blanket semantic verdict for unsupported/invalid tasks. Source/checkpointskept,
noautomaticnewrun. Supersedes ACTIVE347434notices below.

LATEST2026-11-08 explicituser“sửa đi rồi chạy lại”:DSpecproofrepairDONE,
continuationACTIVEcontroller347434/newoutputgrounded_resume_20261108_183913.
DSpec2TestprobePASS5buckets/1encoded/0reference;reusesexact1oldresponse,cached
requestidentityPASS,0freshprobecompletions. FullDSpecchild347652running44tasks;
ISLa next. LISP/CrossHaircomplete sources/plans/outputsymlinkedunchanged,no
regen/rescore. Same44cohort/budgets/seeds/reference/scorer/native/vendor.
PatchonlyDSpecadapter/dafnybridge:exactint/bool-equalitysubstitutionproves
domain/contextFalse→exhaustedwithproof;unknown/feasibleremainnative,othererrors
notrelabelled.49engineeringDSpectests+1controllerreusePASS,nativepass/failsmokes,
frozenqueueguardPASS. Rootqueueprepare now supportsresume_from_candidate option;
defaultISLaonly preserves priorcontinuations. Oldfailedqueuekeptunchanged.
Prefectsame98959f77Running,observer347435followsnewoutputwitholdmapping;
paramsrecordcontinuation_source;artifactb6a95afb-d173-4911-95dc-0db4c292e4a6.
Keepalive330905reused600s,no duplicate. See research GROUNDED_CONTINUATION_STATUS.md
andactualstatuses;do noteditfrozenlive source or duplicatequeue. Pendingefficacy.

LATEST2026-11-08 usercheckGroundedqueueFAILED:controller330903/probe339208exited,
sourceprobe_requires_correction atDSpec2TestinterfaceprobeHumanEval15.
FullLISP44complete30valid/0detected/197responses254167tokens,replayPASS;
CrossHair44complete8valid/0detected/0calls,replayPASS. DSpecfull/ISLa notstarted.
DSpecprobe1response765tokens/0unknown,5buckets/1encodedinput/0referencecalls.
Refinement n==-1 AND domain n>=0 is impossible;nativeDSpec returns2/no reachable
codepoints,adapter maps any nonzero toerror;probe requires witness/exhausted so
fails even though n==1witness exists. No endpoint/truncation failure evidence.
Read-only diagnostic final/review/bucket_grounded_failure_2026-11-08.md attached
samePrefect98959f77/keygrounded-queue-probe-failure;no codepatch/workloadrun.
User only saidcheck;rule9requires explicit launch/resume command. On request,
prepare domain-infeasible handling/native-unreachable classification with proof,
retain first2completed candidates and savedmodelcall/attempt history;do not
blanket-convert errors toexhausted. Supersedes ACTIVE queue notices below.

2026-11-07 user clarifies scope is automatic input identification/generation,
not necessarily complete test generation. Survey and per-paper notes:
[research report](../research/boundary-input-generation-2026-11-07/README.md).
Distinguish unknown-boundary discovery from known-condition construction;
observed execution feedback is not a correctness oracle. SETBVE public repo/docs
verified; AutoBVA/ABEX Zenodo artifacts inaccessible, not code-verified.
No implementation/reproduction/benchmark/model calls/commit. Existing v66/v68
and precision diagnostic constrain novelty/efficacy claims.

Follow-up clarification same day: user specifically asks identifying testing
conditions unmet by base tests or derived from implementation. Report now
separates BVE archive/search gaps, source branch/path gaps and explicit BVA
obligations. CoverUp has existing-suite line/branch gap targeting; CrossHair
cover CLI does not take base-suite coverage; neither establishes semantic BVA
gap detection. Do not answer this scope merely with generic input generators.

Latest user correction supersedes an unnecessarily narrow requirement above:
tool need not analyze base tests first. Defining input buckets from impl/spec,
then excluding buckets represented by base inputs is acceptable. LISP and
DSpec2Test notes added as direct prior work for automated partition definition;
base membership filtering is an adaptation, not a verified author-tool feature.
Do not reject prior work simply because it does not take a base test suite.
Keep exact-input deduplication distinct from removing represented buckets.

User then requests candidates, methods, repo fit and lib/repo availability.
Verified-source shortlist: [CANDIDATES.md](../research/boundary-input-generation-2026-11-07/CANDIDATES.md).
LISP master (Python partition chain + Java runner); CrossHair Python backend
already present in v66; DSpec2Test branch generate-tests/spec (main README is
upstream Dafny); ISLa check/solve API for structured strings. Priorities distinguish
bucket-definition method from construction backend; no new install/run/source edit.

2026-11-07 latest authorization: implement all four candidates in four separate
worktrees, reconsider CrossHair objective because v68 failed. User then requires
plan + subagent review BEFORE worktree creation. Initially created four clean
detached worktrees were verified clean and removed; no implementation yet.
[Implementation plan](../research/boundary-input-generation-2026-11-07/IMPLEMENTATION_PLAN.md)
is under independent read-only review. No source changes/benchmark/model calls.
CrossHair planned change is direct boundary-obligation inputs with independent
post-freeze oracle, not source edits or model-written assertions. Do not recreate
worktrees until plan review must-fixes are resolved.

2026-11-07 implementation COMPLETE in four detached worktrees (same6dcfbd48),
after plan+subagent review and three independent code reviews. No merge/commit.
[Implementation report](../research/boundary-input-generation-2026-11-07/IMPLEMENTATION_REPORT.md).
Paths `/home/phong/dev/ConceptTester-worktrees/buckets-{lisp,crosshair,dspec2test,isla}`.
Final targeted suites10/23/13/11pass, existing modular363pass; live model0 and
benchmark0. CrossHair direct input obligations differs from v68 assertions/edits.
DSpec formal native generation has no bucket export; separate adapter-manifest
filtering/construction mode. ISLa native length fix uses public optimized=false,
not native source edit. LISP live model semantic efficacy untested.

2026-11-07 user authorizes real LLM queue, one at a time. ACTIVE detached
controller289968 at final/out/bucket_candidates_serial_20261107_233900;
launch audit alive/lockheld,waiting_endpoint(LISP first),0task attempts/responses.
Old/new suppliedendpoint404,ERR_NGROK_3200;privateconfig outside repo only.
Readiness polls60s; automatically start exactQwen27/context8192whenavailable.
Order LISP/CrossHair(0LLM)/DSpec/ISLa;existingboundary44cohort,20inputs/task.
No paidfallback. Plan+code review fixes applied before freeze;source/data/native
lock snapshots;liveharness3passed,LISPupdated13passed. Do not duplicate/restart
controller or edit frozen source. See
[live status](../research/boundary-input-generation-2026-11-07/LIVE_QUEUE_STATUS.md)
and exact status/progress/call ledgers before acting. No live result yet.

2026-11-08 user reports endpoint revived; verified exactQwen27/context8192 and
tokenizer13. Existingcontroller289968automaticallyrunningLISPchild303113,
queueflockheld;firsttask0nativepartitioncompletionstarted,1attempt/0responses
at audit. Other3notstarted;no duplicate or source/config changes. This supersedes
waiting_endpoint notice above; check actual artifacts for later progress.

2026-11-08 latest progress: queue289968alive/lockheld now finalISLa402399,
4/44inputtasks,1response+1active. LISPterminal44/82responses/144525tokens,
CrossHairterminal44/0calls,DSpecterminal44/41responses/36200tokens; all3replay
match,0detected,validnovelinputs0/2/0. Mechanismauditpending,zero yield not
semantic efficacy evidence. No restarts or source changes.

2026-11-08 TERMINAL COMPLETE supersedesrunning:all4/44tasks,replayallPASS,
127receivedtaskresponses/190514tokens,0taskunknown. Validnovelinputs0/2/0/0,
detected0all. LISP41adapteroutputsallfenced(37JSONreject/4truncated),DSpec
18fenced+18rootlist+5truncated;3barelisttypeblockseach. ISLa37interfaceunsupported,
3barelist+3truncated,1admittedwronggrammarshape→24unknownmemberships/0construct.
Interface failure,notsemanticinefficacy. No newcalls/repair/restart in audit.
See [terminal report](../research/boundary-input-generation-2026-11-07/LIVE_RESULTS.md).

2026-11-08 user forbids terminal reporting of routine I/O contract failures;
requires autonomous fix+rerun ([[repair-io-contract-autonomously]]).
Repaired schemas/explicit executable examples/native-compiler validation,
lossless fences/rootarray handling,3bounded recorded corrections,6buckets,
no semantic-miss/transport retry as syntax. ISLa supplied native CFG+model formulas.
Independent reviews complete;tests20/33/23/21+transport26pass. Main .venv unchanged;
isolated parent runner .tools/bucket-contract-runner pins jsonschema4.25.1.
Newqueue final/out/bucket_candidates_contractfix_20261108_101300 ACTIVEcontroller
21290alive/flockheld,waiting_endpoint404,0probe/0taskattemptsatlaunch. Each LLM
candidate probe thenfull44 in originalserialorder. URLrequestedasync;updateexisting
privateconfigwhenarrives,no duplicatecontroller/frozensourceedits. Do not report
contractfailures terminal;repairautonomouslyifprobe/postrunrequiresit. See
[repair status](../research/boundary-input-generation-2026-11-07/CONTRACT_REPAIR_STATUS.md).

2026-11-08 endpointrefreshuser: existingrepaircontroller21290automaticallyrunning.
ExactQwen27/context8192/tokenizer13verified. LISP liveprobePASS:3buckets,
1encodedinput,3responses/2920tokens,0referencecalls;no contractfixneeded.
Now full44LISPchild91421,firsttask0nativepartitionstarted;other3queued.
Privateendpointupdatedonlyoutside repo,no duplicate/source changes. Check actual
queue status before acting;preserve frozen worktree source while running.

2026-11-08 user requests results on local Prefect;published existingrepairqueue
as observed flow64c28b68-68bf-4825-b745-f927b8ef063b with4serialtasknodes and
table/reportartifacts. Detachedobserver136739updates15s, no workload calls or
frozen source edits. AtpublishLISP34/44generation,29encoded/131responses;
evaluationpending,other3queued. Persistentmappingfinal/out/run_console/
bucket_observers/. See research PREFECT_PUBLICATION.md and actual Prefect/source
artifacts for later progress;do not duplicateobserver/queue.

2026-11-08 check: repairedLISP COMPLETE44/15validnovel/10detected/171responses;
CrossHair44/2valid/1detected/0calls;DSpec44/3valid/2detected/7responses;allreplayPASS.
RoutineISLa parser compatibility fixed autonomously perrule:single start wrapper
same language/native source unchanged;runtimeTypeErrorunknown. ReviewPASS,
native22tests+continuation3pass. Verified first3original plans/cohort/settings/
task/program/config/archive andreuse unchanged/no newcalls/scoring. Continuation
final/out/bucket_candidates_isla_continuation_20261108 controller142648ACTIVE,
ISLa liveprobePASS6buckets/3inputs/1response1240tokens/0reference;fullchild142994
at3/44generation. SamePrefectflow64c28b68observer142838nowfollowingcontinuation,
API RUNNING. See ISLA_CONTINUATION_STATUS.md. Preservefrozenlive source.

2026-11-08 VERIFIED correction supersedes all prior detection counts10/1/2/2.
All4generation finished;validinputs15/2/3/8. Every original evaluation was
ModuleNotFoundError from numpy in sandbox: isolated schema runner .pth not
bound by bwrap. Corrected zero-model rescore with main benchmark interpreter,
byte-identical original comparator/scorer/reference, exact frozeninputs/cohort,
fresh caches and cold native equality smoke yields0detectedALL4;all28inputsPASS.
Allhash/inputfreeze/replayPASS;0newmodel/tokenizer/constructorcalls.
Artifacts final/out/bucket_candidates_corrected_evaluation_20261108;verified_results.json.
SamePrefect64c28b68tableupdated0all;oldcountsfalsepositivesDONOTCITE.
Future safeguards bind actual dependency roots read-only,updatecacheidentity,
cold equality smoke beforegeneration;read-onlyreviewPASS. See research VERIFIED_RESULTS.md.

2026-11-08 userrequestswhy0detections/inputanalysisCOMPLETE. Saved56encoded
records->28validrecords(27distincttaskinputs),only13/44tasks;none99/124/83.
LISP37proposals/22invaliddomain/15valid;CrossHair8/6invalid/2valid;
DSpec3/3valid;ISLa8/8valid. All samecohort and knownbugsourcehashverified.
Knownsaved99/124neighbors calibrated exactcorrectedruntime/maininterpreter:
6controls x2repeats,4fail/2pass expectedallmatch,24nativeexec/0LLMcalls.
Mechanisms:rawstring→parsedfloatbinding missing99;yearwidthconditionomitted124;
unannotated99/124excludeISLa/formalroutes;83n>2bucketbasecovered3prunesstress;
DSpecbase9choosesx0earlyreturn;CrossHairbase0invalid;manyLISPmissesinvaliddomain.
No newgeneration,benchmarkexpansion or claimedmethodfix. Vietnamese analysis
GENERATED_INPUT_ANALYSIS.md and raw final/out/bucket_input_analysis_20261108/analysis.json;
publishedsamePrefectflow as input-analysis/input-coverage artifacts.

2026-11-08 user yêu cầu sửa rồi giải thích4pipelines: applicability repair DONE
ở bốn worktree hiện có, uncommitted; vendor/native giữ nguyên. Independent
plan/code reviews đã xử lý must-fixes; final full engineering suites191checks
PASS (41/56/46/48, có shared tests lặp);0newmodel/benchmark runs. Efficacy sau
sửa CHƯA ĐO, old corrected detection vẫn0all. Xem research/boundary-input-
generation-2026-11-07/PIPELINES_AFTER_REPAIR.md và REPAIR_VERIFICATION.json;
HTML cơ chế tương tác final/slides/bucket-pipelines/pipeline-ideas.html. Report
đã attach+verify cùng Prefect64c28b68, artifact93f620d8-e88d-4ed7-a3ce-e0b8ecf1c80c.
Resource-stress/arbitrary projection inverse chưa được giải quyết; không tự chạy
lại khi user chỉ yêu cầu sửa/check.

2026-11-08 user explicit freshrun afterrepair:groundedqueue
final/out/bucket_candidates_grounded_20261108_171000 ACTIVEcontroller330903,
observer330904,keepalive330905single600s. ExactQwen27/context8192/tokenizer13
readiness+coldsandboxequalityPASS. LISPliveprobePASS6buckets/2inputs/5responses/
3897tokens/0unknown/0reference;full44child331272generationstarted. Other3queued
serial. Same44cohort/input20/seeds/native20s/caps968,0,132,132;reserve3correction
slots avoids capoverrun afterrefinement. Frozenhashes/archive;do notedit/relaunch.
Prefectnewrun98959f77-8974-4e8a-b040-d34a02503f11,configartifactverified. Read
GROUNDED_RUN_STATUS.md and actual queue/status beforeaction;noefficacyresultyet.

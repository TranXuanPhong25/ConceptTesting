---
name: research-state
description: Hub for the thesis direction (concept-guided LLM test generation, TrickCatcher setting): where everything lives, current status, next steps
metadata:
  type: project
---

**Thesis:** LLM test-case generation guided by **concepts** (must stay central, see [[thesis-concept-requirement]]).
2026-11-05 user authorizes plain+BVA run on existing boundary group. Smoke6PUT
configured/frozen in final/out/boundary_smoke_plain_bva_20261105,67sourcefiles,
input20perarm/task,target1,expectedQwen27/context8192,max18logicalcalls;60checks
pass. Storedendpointmodels404;asked forcurrentendpoint,0completions/nocontroller.
See [[boundary-test-applicability]] and final/review/boundary_smoke_run_2026-11-05.md.
2026-11-04 latest user steering:main pipeline now accepts InputGenerator via
dependency inversion;input-producing stages compose with MethodInputGenerator.
Removed initial concept/witness stages from modern flow,default plain;BVA remains
opt-in.Legacy adapter explicit.Shared input contract→freeze→reference→evaluation;
validation functions/START-ENDblocks.93checks pass,no live model/cohort run.
See [[boundary-test-applicability]] and final/modular/generators/README.md.
2026-11-04 BoundaryArm now integrated into main BenchmarkPipeline/CLI opt-in:
fixedtaskbudget→perPUTBVA→dedup→freeze→reference→evaluation/report;explicit skips,
boundary-only noCFG/witness work.85modularchecks pass;no live model/cohort run,
no default-arm change or commit. See [[boundary-test-applicability]].
2026-11-04 BoundaryValueAnalysis module implemented at user request in existing
final/modular/boundary_value_analysis:input types→templates→LLM boundary/domain
selection→LLM inputs;early skips,immutable cache,41engineering checks and6PUT
offline extraction pass. Prose constraints remain unverified;no live LLM/PUT/
reference run,default-arm integration or commit. See [[boundary-test-applicability]].
2026-11-04 16:38Vietnam:83538active/stilltask139;PUT5 preparation_failed/RuntimeError
after~60min,nowPUT6 factworker84585~100%CPU54min. Inputs139/responses268/scored0;
keepalive16:23received,no edits/restart. See [[final-humaneval-pipeline]].
2026-11-04 15:23Vietnam:concept-inputs83538active,stilltask139/PUT5 factworker;
nativePython83762~100%CPU for40min,heartbeatcurrent/idle0. Inputs139/responses268/
scored0 unchanged;keepalive15:03received,no newerror/restart. See live artifacts and
[[final-humaneval-pipeline]];serviceactive alone does not mean task progress.
2026-11-04 14:43Vietnam user supplies endpoint;concept-inputs resumedPID83538 at
HumanEval139 extraction,actual fresh response received. Metadata27B/8192/tokenizer
verified,105sourcehashes unchanged,139savedinputtasks reused. FullV11stopped;
supersedes failed notice below. See [[final-humaneval-pipeline]] and live status.
2026-11-04 latest status check: no local experiment running. Concept-inputs service
failed10:40:04Vietnam,tokenizeHTTP404 during HumanEval139 concept extraction;
MainPID0/statusinterrupted. FullV11inactive;no restart. Supersedes active notices.
See [[final-humaneval-pipeline]] and live output status/events.
2026-11-03 user wants separate boundary/equivalence/C1/def-use development from
test_slides, small subsets before combining.164tasks manually reviewed in
final/review/development_groups/, offline selector final/development_groups.py.
6PUT smoke/group exported,dev≤12/check4;9checks+independentreview pass;no new
model/native outcomes. Existingconcept-inputsservice36821active/source105unchanged.
See [[four-course-development-groups]]. This is subset preparation,not4newgenerators.
2026-11-02 final/ latest: user stopped fullV11 at288/1634durable results;4533saved
artifact hashes preserved,service inactive/STOP marker. New v11_concept arm added
in existing final/modular code: oldV11 mining/facts only → modern one-call/task
inputs-only generator → reference. Changes uncommitted for user review; no new
benchmark launch/outcomes. Latest workflow edits existing code rather than copying
new version folders. See [[final-humaneval-pipeline]]. Overrides older run notices.
2026-11-01 final/ TERMINAL COMPLETE164/157eligible;plain78/classical74/contrast78
raw;matchedprimaryp.7483,no demonstratedconceptgain. User-requested class/module
refactor final/modular ready15checks/164read-onlyreplay/2296events,fullsummary
parity;23originalhashes unchanged,0newcalls/nativebenchmark,nojobs. Eacharmmodule,
eachstageclass,insert_stage for extension. Newpipeline/refactor staysuncommitted.
See [[final-humaneval-pipeline]];allolder running/waiting notices superseded.
2026-10-31 12:17UTC final/ endpoint recovered;auto-resumedcontroller121309 and
scheduler115270 alive. Inputs99/164,487responses,0scored;99/100firstattempts
inflight,93/94cleared. User continue;no duplicate/source/cohort changes. Older
waiting notices superseded;see [[final-humaneval-pipeline]].
2026-10-31 10:59UTC final/ scheduler115270 WAITING_FOR_ENDPOINT/models404;
controller115608 exited tokenizer404(no new completion sent).Inputs93/164,
458responses,0scored;93contrastive/94classical partial streams archived,never
used. Cached cohort unchanged. Metadata-only polling;automatic resume on live
expected model,no duplicate scheduler. Older running notices superseded.
2026-10-31 09:34UTC final/ recovery alive115608/115270;inputs81/164,
395responses,0scored,task81/82inflight. Task41/placebo timeout automatically
recovered;partial archived,neverusedassuite. Legacy16+41historicalunknowns
retained. No new launch/repair;older counts superseded. See [[final-humaneval-pipeline]].
2026-10-31 07:04UTC final/ recovery RUNNING controller115608/scheduler115270;
inputs26/164,131responses,task16cleared,2inflight/0newunknown,0scored. Frozen
cohort164/1634PUT/1465basepass unchanged. Inspect recovery/status.json;older
waiting/stopped notices superseded. See [[final-humaneval-pipeline]].
2026-10-31 final/ transport recovery READY42checks/reviewclear;user requests fix
and retry after20min. Scheduler115270 waits06:38:15UTC/13:38:15Vietnam;endpoint
currently404,metadata-only polling afterdeadline untilready. Original cohort164/
1634PUT/1465basepass reused;331artifacts/91responses/18inputtasks imported with
hashes,92requests identical. Streaming + persistent3attempt cap, no model/source
method changes. See [[final-humaneval-pipeline]] and recovery_schedule/status.json;
controller not started at release,no duplicate scheduler. Older notices superseded.
2026-10-31 final/ readability-audit status: controller107832 exited/interrupted;
cohort FROZEN164tasks/1634PUTs/1465basepasses.18inputtaskfiles,0scored;tester
task16/classical1unknown,plus historicalwriterunknown retained. User asked code
readability review;no APIretry/source changes in this turn. See [[code-readability]]
and final/review/READABILITY.md. Older running notices below superseded.
2026-10-31 final/ USER RETRY RUNNING controller107832;metadata200/samemodel8192,
source hashes unchanged,1603cachedfiles preserved. Reuses118tasks/1175PUTs/
1086basepasses;originaltask118unknown archived/accounted;retryinflight,new119
response received. No tester/scoring yet. See [[final-humaneval-pipeline]] and
live status;older stopped notices below superseded,no duplicate launch.
2026-10-31 latest final/ status: controller93111 exited;interrupted RuntimeError
from ModelError task118/programs_00,1unknown/noresponse. Durable cohort118tasks,
1175PUTs,1086basepasses (117mainprogress+1drained).0tester/scored tasks. Endpoint
currently200/samemodel;jobisnotrunning. Preserve caches/no blind unknown replay.
See [[final-humaneval-pipeline]];older running notices below superseded.
2026-10-30 latest: user clarifies fixed-PUT concept-utility benchmark with actual
reference oracle;generate cohort once,alllaterconcept runsreuse. New isolated
final/experiments/concept_reference_v1 with library CFG/DFG/boundary/partition,
classical/plain primary + contrastive/placebo/toolinput/witness controls.27checks,
164canonical pass;realqwen3.5-27b-awq33tokenprobe pass,ctx8192. Full164 detached
controller93111 launched buildingcohort;inspect final/out/concept_reference_v1/
status.json and cohort status before action. No efficacyresult/no duplicate launch.
See [[final-humaneval-pipeline]];old waiting-for-endpoint notice below superseded.
2026-10-30 user-requested independent `final/` pipeline READY, awaiting user model/
endpoint. Scope explicitly all164HumanEval;10structurally distinct programs/task,
base filtering,1sharedtester call/task,additional-failure metrics.17engineering
checks+164/164canonicalpreflight pass;review complete;0realmodelcalls/nobenchmark
results. See [[final-humaneval-pipeline]] and final/README.md;do not substitute an
old backend or auto-launch before user sends the selected endpoint/model.
2026-10-30 vr15 COMPLETE after user requested improvement: domain evidence and
two composites;33tests+independent prefreeze review. Census67→69tasks,131→147
instances,5edges/3tasks;all16newinstances/5edges conditionally source-supported.
Directlookup=structuredBM25(147bindings),no retrievalincrement;partitions remain
unexecuted and sometimesunreachable.0model/targetcalls,noactivejob/defaultchange/
v11integration/automaticVR16;VR14frozenpreserved. See [[concept-template-query-direction]].
2026-10-30 vr14concepttemplates COMPLETE: user-approved source-only prototype,
20tests + independent review/freeze. Authored bindings10/16raw vs16/16structured;
unlabeled census56→67/113bindingtasks,98→131instances,zero relationedges.
86/131cardinality; structuredarmsidentical, task51replacementdomainunknown.
No demonstrated relational/efficacygain,0model/targetcalls/canonicaluse;noactivejob,
defaultchange/v11integration/newtestgen. See [[concept-template-query-direction]].
2026-10-29 vr9 CPU READY, endpoint BLOCKED404: user-authorized applicability+
retention repair aftervr8.48CPUchecks/12exactcontrolreplays pass;CPUselected19→24,
task51zero→4. Expected outputs/final scoring pending,0newcompletions/tokens;
controller64941exited. Frozen same6tasks/savedpools;max12fresh expected-outputcalls.
See [[vr9-applicability]];no activejob/automaticfull113/vr10.
2026-10-29 vr8 COMPLETE6tasks/3arms:ref6/6FA0each,alreadyR1ceiling;no semantic gain.
Onlytask51changed targeting:correct vowel table makes disagreement predicate
impossible;200valid candidate occurrences discarded,including native-confirmed
exposing input.20newresponses/18,108tokens,0unknown;41CPU+hash/receipt auditPASS.
PID35827exited;no activejob/automaticvr9/full113. See [[vr8-semanticgate]].
2026-10-29 concept/cost audit:retrieval generation154vs268calls,187568vs273274
known tokens;full shared-cost attribution−9.24%.206/275bindingsuseSTMT,204hitR1;
coverage proxy does notmeasurecardsemantics.8pairedlossesmissinput,1oraclefailure.
ConceptCoderdefinition audit+5data-onlydrafts saved;no runtimechange/newinference.
See [[v85-concept-quality]];this ismeasurementproposal,notclaimed efficacygain.
2026-10-29 07:04UTC latest: v85 COMPLETE113pairs/1130refs/113scored;PID46002 exited.
Primaryref retrieval78vs v11 77,FA10vs13,paired10-9,p1.0:no clear primary gain.
Secondaryo0 73vs61,FA51vs57,p.01690;do not replace primary.2048attempts,4unknowns.
Finalreport/artifacts under v85_20261029_resume2/completed;all running notices
below superseded. See [[v85-retrievalhybrid]];no automatic new run.
2026-10-29 03:31:22UTC latest: Mac resume2 PID46002 from newer Linux174refs.
User confirms Linux stopped;old Mac44302 drained/stopped after13duplicate calls.
113pairs reused,956refs remaining at launch;18historical attempts include4unknowns
and13known duplicates. See [[v85-retrievalhybrid]];all prior running notices superseded.
2026-10-29 03:23:48UTC latest: user explicitly resumes local execution. Portable
runner PID44302 RUNNING;113pairs reused,shared refs37/1130 at first check,
937received total,0new failures,3historical unknowns; scoring follows refs.
See [[v85-retrievalhybrid]] for active work root; older stop notice superseded.
2026-10-29 latest: v85 USER-STOPPED for another machine. PID76780 exited
17:19:23UTC28Oct;113paired generation+36/1130refs saved,936received responses,
0outstanding requests,3historical unknowns.1094refs remain then scoring.
Portable checkpoint: trickcatcher_linefacts/handoffs/v85_20261029/README.md.
Do not restart local inference; older running notices below are superseded.

2026-10-25 v61 terminal: ngrok integrated pilot108responses/6cases and postfreeze scoring complete, independent artifact auditPASS. All18writer hypotheses rejected: intended concept treatment never instantiated. Explicitpattern1/6confirmed, otherfourarms0/6; not concept-efficacy evidence. See [[v61-pathfault-integrated]] and `analysis/v57_completion/RESULTS_V61.md`. Sparse scheduled callback handled, no owned job remains active.

2026-10-25 terminal pathfault (supersedes launch below): v63 continuation complete/audited108responses, fivearms pattern1/6confirmed others0/6.14admitted/57nativewitnesses but hypothesis semantics weak, no conceptgain; actual447667tokens. Scorerlabels provisional, noactiveownedjobs/observer. Read [[v63-scopeguard]].

2026-10-25 latest pathfault: v62 writer contract works14/18admitted but case85empty-scope verifier crashed. Reviewed v63 isolated continuation launched01:21UTC, reusing6writers/5checkpoints; remainingarms pending.30min observer, no efficacy verdict. See [[v63-scopeguard]].

Setting = TrickCatcher EvalPlus: LLM-written PUTs pass the HumanEval base tests but are buggy; the generator gets
spec (docstring) + PUT code + base tests and must write assertions that reveal the bug. Model: Qwen2.5-Coder-7B-Instruct
(fp16, vLLM 0.7.3) served from the user's Kaggle notebook through ngrok (see [[working-rules]] for how to use it).

**Where things live (all under `trickcatcher_linefacts/`):**
- `RESULTS.md`: every result, numbered sections (§11.x is the latest work; §11.43–11.47 on 2026-10-14).
- `PREREG.md`: append-only registrations, amendments and decisions; the "Final comparison protocol" (six fairness
  fixes) is at the end. Register before running; never edit old entries.
- `CONCEPT_WEAKNESS.md`: why concepts are weak (3-layer loss analysis), ranked plan; section 4 = current fix plan
  (S1–S5 small, B1–B5 large) with progress notes.
- `PLAN_BASELINES.md`: baselines (CoverUp, MuTAP, SymPrompt, ACH, TrickCatcher-full) and held-out (VibePass, MBPP+).
- `pipelines/<version>/`: self-contained pipeline copies, each with `CHANGELOG.md`; `pipelines/README.md` lists stages.
  Best = `v7` (+ v8-strict construction). `v11_fair` = v7 + fairness fixes (dev GPU results complete, §11.41). Dropped: v9_callfb,
  v10_spechint, v7_mutref (as main rule). `v7_vp` = v7 working inside class methods (VibePass).
- `baselines/`: symprompt, ach (reimplementations, approved), coverup, mutap (adapters), tc_full_v2 (TrickCatcher-full,
  repr serialisation). `heldout/`: MBPP+ and VibePass builders. `analysis/`: analysis scripts and outputs.
- `out/`: runs (`out/gen2_qwen7b_v7hyb_v4_r2` + `out/oracle_v7hyb` = v7 run of record; `out/gen2_qwen7b_v8strict_est`).
- Repo root `CONTEXT.md`: older checkpoint notes (2026-10-11..13) with run commands; `HANDOFF.md`: 2026-10-07 state
  of the other (earlier) projects.
- Diagram (private claude.ai artifact, Claude can update): https://claude.ai/artifact/7a6yvf5bhiVmZVyt9UvTC8
  ([[version-tree-diagram]]).

**Method (v7, best):** tool computes concept facts (code facts: MUTANT/STMT/OUTCOME/BOUND/REL/DU…, mined input validity,
spec input-class facts) → picks 3 hints with fuzz witnesses → arms (plain, concept, toolinput, gen-plain, concept-hybrid,
placebo-hybrid, plain-hybrid; K = 3) → round 2 = Hypothesis strategy per missed hint (strict: only tool-verified inputs)
→ oracle ref (10 spec-only DPP programs, unanimous) / full (+ judge + postconditions) → per-task sign tests.

**Key results (dev, 113 HumanEval tasks; numbers = bugs found per run under ref):**
- v8-strict: concept-hybrid 61.0 vs plain-hybrid 55.7 (per task 29/20 n.s.); vs placebo-hybrid 33/13; toolinput ≈ 64.
- Random-subset matched count (§11.38): concept-hybrid vs toolinput 54.2 vs 62.5 (26/40, p=.11); vs plain-hybrid 43/26
  (p=.053); vs placebo 42/23 (p=.025).
- Witness-only, no LLM (§11.37): 43.0 with 1.4 calls; toolinput 64.7 → ~2/3 of toolinput's bugs are already in the
  fuzz witnesses. Witness-only is now a mandatory baseline.
- Rank-2 hint selection (mutref, §11.39): no gain on odd tasks (13/10 vs old rule). Rank-5 BEHAV (§11.35), v9 concrete
  calls + feedback (§11.36), CrossHair (§11.33) gave nothing. MBPP+ real-12: no concept advantage (§11.32).
- Main loss = fault-hypothesis gap (VibePass metrics §11.28): Qwen follows hints poorly; round 2 is where hints help.

- v11_fair dev sanity (§11.41, real strict, matched placebo): concept-hybrid 61.0, toolinput 64.3, placebo-hybrid 57.7
  (was 45.7 with fewer round-2 requests), plain-hybrid 55.7; concept vs placebo only 26/22 → most of the old "beats
  placebo" came from the extra round-2 requests, not hint content.

**Defensible claim now:** the tool yields grounded facts with witnesses and the complete pipeline beats paper
baselines; NOT yet shown that an LLM reading concepts beats plain, matched placebo or toolinput under fair conditions.

**Next steps (CONCEPT_WEAKNESS.md §4):**
1. B3/B4 and repaired v14/v15 completed (RESULTS §11.45–11.47). B4 native score initially lacked task 44;
   unchanged single-worker retry completed it, full 133/133 cohort verified. Hypothesis pipeline lost to flat/toolinput
   on dev; no promotion. All queue jobs ended; see GPU_QUEUE-2026-10-14.md and analysis/b4_v13_hyp_results.md.
2. v14/v15 GPU smoke completed on 20 dev tasks/K=1: both produced zero accepted semantic cards, so only generic
   fallback/control arms ran. RESULTS §11.44 and analysis/v14_v15_gpu_smoke.md/json; see [[linefacts-new-trials]].
3. v11_fair dev and five paper baselines are complete (RESULTS §11.41–11.42). Held-out VibePass 66 + MBPP+ 12 awaits
   final arm choice and Qwen availability, with the frozen protocol and runbook.

**New direction requested (2026-10-14):** user wants more abstract concepts over control/state/input-output
behavior, potentially symbolic execution/pseudocode, and asked for a plan. See [[abstract-concept-direction]]
and PLAN_ABSTRACT_CONCEPTS.md. User authorized implementation immediately on 2026-10-15, overriding the benchmark wait. v18_modelselect selection-only pilot complete (no MCTS):52 tests,13/20 base-consistent menus,12/20 sampled-consistent retained/displayed requirements; LLM11 vs lexical-rule12 vs uniform9.17.119 canonical-confirmed input discrepancies across12 tasks,0 observed property false alarms, no D_IO/generation (RESULTS §11.52). Future matched generation comparison needs a separate protocol; LLM selection gain not shown. See [[abstract-concept-direction]].

2026-10-15 v19_rulegen: user authorized implement/run; code+prereg complete, CPU gate passed. GPU launch attempted but tunnel offline;0 generation requests, no D_IO. See analysis/v19_rulegen_status.md and [[abstract-concept-direction]].

2026-10-15 UPDATE superseding v19 waiting status: v19 generation/scoring complete and frozen hashes verified. No missing work/GPU job. No concept generation gain; output format bottleneck. See RESULTS §11.53, analysis/v19_rulegen_results.md/json and [[abstract-concept-direction]]. New interface experiment not yet authorized/started.

2026-10-15 UPDATE: user requested plan→subagent audit→implementation. v20 narrow CPU multiplicity increment completed after two independent plan/code audits; final folder v20_groundedflow_domainfix, earlier failures preserved. No running GPU job, no D_IO. Read PLAN_GROUNDED_FLOW_V20.md, analysis/v20_plan_review.md, v20_cpu_results.md and RESULTS §11.55 before expanding scope. Real-task requirements remain unreviewed; guards/loops/derived provenance not implemented.

2026-10-15 latest direction correction: user wants Qwen semantic extraction/alignment through prompt chaining, rejects static property/effect text matching as the main method. See PLAN_QWEN_REASONING_CHAIN.md and [[abstract-concept-direction]]. v20 is only a narrow verification prototype. No chain implementation/GPU started; independent plan audit required before code.

2026-10-16: Qwen-chain detailed plan v3 independently audited by two subagents, blockers resolved. PLAN_QWEN_REASONING_CHAIN.md + analysis/qwen_chain_plan_review.md define five stage contracts, direct-tuples first pilot, budgets and separate semantic/observation labels. Plan-only deliverable; no v21 implementation/GPU started.

2026-10-16 scheduled Qwen-chain thread: v21_qwenchain P1 offline interfaces complete/reviewed; source copy from best v7 and final snapshot. No Qwen/GPU/canonical/ref/D_IO; future model run still requires explicit request. See [[qwen-chain-offline]] and analysis/v21_offline_interfaces.md. Parallel flowtools plan unchanged.

2026-10-16 Qwen calls now explicitly authorized; v21_qwenchain_pilot controlled16 running detached with frozen source,74 preflight checks, two independent reviews. Read analysis/v21_qwenchain_pilot_status.md and out/runlogs_v21_qwenchain_pilot/status.json. Human semantic gate pending; no real20/D_IO, do not start duplicate or repair active treatment.

2026-10-16 Qwen-chain update: explicit model-call authorization exercised; two controlled16 pilots complete/frozen. Singlejson adaptation S1 13/16,S2 3/16,S3 three abstentions; gate19/62,probe0/7. Our empty-guard contract gap + f12 semantic alignment miss documented. No generated inputs/real20/D_IO. Read [[qwen-chain-offline]] and analysis/v21_qwenchain_singlejson_results.md; callbacks handled, do not duplicate.

2026-10-16 user-requested v22 fixes + separate S3 replay complete. Guard contract fixed/89 offline checks; full pilot gate24/62,probe1/7,6 S4 inputs/0 S5 final. Old f12 raw mismatch recognized in S3-only replay but invalid status, ambiguity remains weak; no reliable semantic-success claim. See [[qwen-chain-offline]], RESULTS §11.59. No GPU work running; callback already handled.

2026-10-17 v25_interface_gate: user authorized continued implementation and old endpoint when GPU ready. Audited prospective split-output feasibility5,74 source files/prepared data/dependencies frozen; staged A/B/C early-stop only. See [[linefacts-v25-interface-gate]], RESULTS §11.64 and analysis/v25_cpu_audit.md; inspect owned status before any action, never duplicate or auto-expand to comparison/benchmark.

2026-10-17 v25 terminal supersedes launch: transport-incomplete, no task response; A failed, B/C blocked. f02/f04 timeout, f06 completion503→404, f14/f13 tokenizer HTTP errors. Only capability echo42/10tokens known;8task attempts usage unknown. Frozen hashes verified, independent review/callback handled; no retry/reset/auto-expansion. Read [[linefacts-v25-interface-gate]] and RESULTS §11.65.

2026-10-17 user authorized tiny transport retry after10min. Detached probe scheduled14:08:06UTC/21:08Vietnam in fresh out/transport_probes/v25_20261017_140806; max2single-attempt completions, no diagnostic5/benchmark chaining. Frozen original v25 preserved. See [[linefacts-v25-interface-gate]], RESULTS §11.66 and transport probe audit; inspect status, never duplicate.

2026-10-17 transport probe terminal supersedes schedule: models GET404/ERR_NGROK_3200, endpoint offline at21:08Vietnam;0tokenizer/plain/guided completions.0unknown completion usage for this probe; old8unknown attempts unchanged. Source/original hashes verified, independent review/callback handled, no retries/new calls. Read [[linefacts-v25-interface-gate]] and RESULTS §11.67; no active run.

2026-10-18 explicit fresh transport retry complete: v25_20261018_040624 models GET404/ERR_NGROK_3200 at11:08Vietnam,0tokenizer/plain/guided completions. No unknown generation usage for this run. Original artifacts verified unchanged, no automatic further retry/diagnostic5. See [[linefacts-v25-interface-gate]] and RESULTS §11.68; callback handled.

2026-10-18 this Qwen-chain thread: user-authorized Luna subagent diagnostic complete,6/6 valid vs Qwen0/6 on same6 saved targeted messages (3S2/3S3). Strong model-capability signal, harness/budgets unmatched, no full chain or D_IO. See [[qwen-chain-offline]] and analysis/luna_chain_probe_20261018/REPORT.md.

2026-10-18 user-authorized native v23/v24/v25 Luna/low retest launched16:36UTC, fresh model-probe roots; no Qwen endpoint calls. v25 A failed on validator comprehension-scope false rejection despite faithful normative code; v23/v24 still running. Execution host disabled but schemas exposed, no matched harness/causal model claim. Read [[linefacts-luna-version-retest]], RESULTS §11.70 and explicit statuses before action.

2026-10-19 correction/continuation: Luna nativev23/v24 had stoppedquota at73/65accepted+oneunknownattempt each. User explicitly authorizes continue. Fresh continuation root imports acceptedoutputs/caches exactly; max87/25missingstagecalls, quota access confirmedbyfreshv23responses beforev24launch. No original/v25repair or duplicatecalls, externalold+newcost needed. See [[linefacts-luna-version-retest]] and RESULTS §11.71.

2026-10-19 Luna native retest COMPLETE16/9/5: v23C/D/H5/7,7/7,5/7correctassertionbugtasks,FA1/0/0; v24verifiedselected1/3 vscontrols/witness3/3; v25Afailedvalidatorlegitimatecomprehensionreuse, B/Cblocked. No concepttaskgain, rawsemantics largelyfaithful; serialization/scope/gatingmechanismlosses found. Allold/frozenoutputsunchanged, noactivejobs/retries, noauto widercomparison. Cumulative253CLI/251responses/2quotaunknown; read [[linefacts-luna-version-retest]], RESULTS §11.72 and fullreport/verifier/reviews.

2026-10-19 v32_scope_support: user-approved stdlib comprehension scope/cumulative support fixes in separate best-v7+v25-port folder;48 CPU pass, clean-context audits. Fresh Luna seen5 Atrue/Bfalse/Cblocked: all4 contracts calibrated, f02/f04 supported, f14consistent/f13unknown; f06 correct fault condition but wrong trigger signature and misleading evidence sentence. Scope fix exercised, support promotion CPU-only, no model inputs/comparison/gain.22calls163666/4463tokens0unknown,old/frozen inventories unchanged,no active job/retry. See [[linefacts-v32-scope-support]], RESULTS §11.73 and analysis/v32_scope_support_20261019/REPORT.md.

2026-10-19 Qwen-chain thread OpenRouter30dev authorized and completed: v32_qwenchain_or30 exactqwen/qwen3.5-35b-a3b,93completions,$0.05124. S1/S2valid29/28,S3selected3,S4inputs18; canonical any-stage IO3/30,final-S5 IO0/30(all3S5ID/aliasfailed). Promising rawsemantic/input examples, interface stillblocking. All source/gen/evidence frozen/verified; no activejobs/newspend. See [[qwen-chain-offline]] and analysis/v32_qwenchain_or30_results.md.

2026-10-20 Qwen-chain followup: user requests same30 chain vs direct with GPT-5.6 Luna/low; v33_lunachain30 frozen/launched,99 CPUchecks+canarypassed. Max300taskCLIcalls/2workers,no paid API or automatic unknown retry. Read [[qwen-chain-offline]] and own status before action; source frozen, canonical score withheld till generation complete.

2026-10-20 v33 Luna chain/direct30 COMPLETE (supersedes launch): chain8vsdirect25value-unequalcanonical tasks(strictdirect26,type-onlytask130),final8vs21,nochain-only.14terminal+7groundingblocks hurtchaincoverage;6blocks legacy12-refcap not advertised. No gain even equal-input8vs8.37(shared9).253taskCLIresponses,0unknown/tools;noactivejobs or newcalls. Do not promote this hard-gatedchain; see [[qwen-chain-offline]]/RESULTS11.75/report.

2026-10-20 fault-concept line (v31→v34→v35, Qwen3.5-35B OpenRouter, vibepass_half): v31 fault-template 18 vs plain 15 (4–1, weak); v34 vs same-input placebo 8–2 but FA 27>23, rule not met; post-hoc concepts point at the bug in 11/33, 5/8 wins use no exposing concept; v35 CPU ceiling 14/33 < 17 → registered **stop**. Cap = template input pool (exposes 17/33 < plain Qwen 19/33), not site location. See [[v31-faulttemplate]], [[v34-ftplacebo]], analysis/v35_concept_ceiling/RESULTS.md.

2026-10-20 direction review (Claude, user asked): proposal "semantic chain + fault concept/template + property oracle" judged no-go as a new run — prior art v23/v21_flowtools/v28, no complementarity (v33 chain-only 0 tasks, 10/17 direct-only end S3 unknown; template ranking ≈ random; template pool < plain). Use the three-branch table (requirement→mismatch, fault hypothesis→input, property→oracle) as thesis "what was tried" with mechanism-explained negatives. Untracked analysis/v36_llm_localize/probe.py (other session, 22:30) has no PREREG.md and targets localization, which v35 says is not the bottleneck; not touched. See [[check-version-tree-before-proposing]], [[signal-not-more-data]].

2026-10-21 Astra D1/v40: usercontinue withquota100%, stop<=15%. Astra7conceptdesign completed; v40best-v7+v30ports code/CPU12/clean audit pass, source/prepared frozen,16sharedobservations32workers. Prelaunchendpointmodels404 =>0Qwentaskcalls,all72slotsnotattempted; noactivecontroller, waitingliveendpoint. PriorCLI schedulefailedactivewriter,notasuccessfulresume. See [[astra-concept-agent-diagnostic]], RESULTS§11.78 and analysis/v40_concept_agent_20261021/REPORT.md.

2026-10-21 v40terminal supersedesreadiness: delayedexactQwen32B launched05:23:51UTC/quota54; models+tokenize received, completionE3CAturn1failedtransport180.101s.1unknownusage/0response/71unattempted; nosemantic/toolresult orconceptgain. Independenthashaudit89source/8prepared/162terminalfilesPASS, no genfreeze/repair/retry/reset. Callbackhandled/noactivecontroller; see [[astra-concept-agent-diagnostic]], RESULTS§11.79 and analysis/v40_concept_agent_20261021/TERMINAL.md.


2026-10-21 v40 explicit retry terminal: new d1_retry_20261021 stopped exactmodel/
context preflight after1received/models metadata;0tokenizer/completion/newworkers,
all72notattempted. Body not saved, alias vs context failure cannot be separated.
Original1unknown completion untouched, no semantic conclusion/automatic further
calls. Frozen source/old inventory unchanged; see [[astra-concept-agent-diagnostic]]
and RESULTS§11.80.


2026-10-21 v40 retry2: user requests anothertry; one savedmetadataGET confirms
currentserver advertises7B/context16384, required32B alias absent. Conditional
32BD1 notlaunched,0completion/newworker calls, all72notattempted. This is not
retrospective metadata or loadedweights proof. Original1unknownusage retained.
No automatic retry/substitution; see [[astra-concept-agent-diagnostic]], RESULTS§11.81.


2026-10-21 v40 retry3 RUNNING supersedes prior7Bmetadata stop: user retries after
32Bservedlabel; liveGET confirms32B-AWQ/context8192. AuditPASS, detachedcontroller
3050555 launched13:20UTC. Firstactual32B response/schema-valid event observed;
semantic correctness/utility not yet reviewed, latercalls running. No duplicate
launch/treatmentrepair. Quota81%, stop<=15, terminalcallback queues originalthread
for all8×3 postfreezeaudit/costs. See [[astra-concept-agent-diagnostic]].

2026-10-21 focused prior-work comparison requested by user COMPLETE: KITE,
ReProAgent, UnitCon and RTED method/source review with supplementary novelty checks.
Generic RCA/trigger/test/feedback/hypothesis discrimination cannot be claimed new.
Conditional proposal focuses semantic validation and adaptive queries, reusing v40
mechanism diagnostic rather than another chain. Latest v41 CPU no-go incorporated;
no new inference/reproduction/benchmark in this research task. Read
[[concept-priorwork-proposal]] and linked final report before proposing more work.

2026-10-21 user grants autonomous concept-research follow-through. Saved-data audit
of complete v40retry3 (72responses,65acceptedturns) and v41 now gives **no-go** for
the proposed concept/adaptive package: all3arms discover same4/4 unsupplied-witness
episodes, CA has concrete semantic retention/revision failures. No D2, larger run
or training launched. See [[concept-research-autonomy]]; owner lifecycle reports
remain untouched and no new model/native execution was needed for this decision.


2026-10-21 v40 retry3 terminal COMPLETE/REVIEWED supersedes running status.72/72
Qwen32Bresponses,all3arms6/6buginputs and4/4newtaskdiscoveries beyondsuppliedshared
rows,0concept-onlywins. CAsemanticcapability failsE2/E4correct-Hretention,E6dedup
evidence andE3wrongbinding; E7finalnoFA,E8unknown. CombinedpackageNO-GOperprereg;
no automaticrun/benchmark/training. Actualknown241789tokens+original1unknown
cumulative;126newnativeworkers+32historicalshared reusedonce. Clean-context2semantic
audits+integrityPASS,callbackhandled. See [[astra-concept-agent-diagnostic]],
RESULTS§11.82 andanalysis/v40_retry3_20261021/REPORT.md beforeproposingmorework.


2026-10-22 v43RUNNING: user-authorized conceptidentification tools implemented,
CPU19/auditsPASS,60source/eightpools78savedrows frozen. No per-taskAstrabinding,
initialQwenproposals+pairedraw/tool finals,max24calls/no newPUT. Readiness1STOP
8359 preserved; prospectivepre-inferenceengineeringamendment/readiness2READY
max4748, originaltreatment/cap/scientificgateunchanged. Detachedcontroller3162510
launched17:37UTC21Oct (00:37Vietnam22Oct),quota53%>15. Noefficacyresultyet, do not
duplicate/edit/reset. See [[v43-concept-identify]] andownedcallbackwhenfinished.


2026-10-22 v43terminalCOMPLETE/REVIEWED supersedesrunning:18responses+6blocked=24
slots, rawcompletebinding+judgment1/8,tool2/8,soletoolsemanticwinE5/0loss,no-go
(original>=2wins/toolvalid8required;actual5). E3correctrawbindinglosttoschema;
E1/E6initialinvalid too. E7falsebug→unknownnotcorrect;E8bothinventfirstsuitable.
Allsource/pool/parent/generation/terminalhashesmatch,independentauditscomplete.
33,208knownv43tokens/0unknown,66HTTPincludingbothreadiness;0newPUTworkers,78saved
rows reused. Originalv40unknown separate. Noautomaticcalls/repair/benchmark.
See [[v43-concept-identify]] andanalysis/v43_concept_identify_20261021/REPORT.md.

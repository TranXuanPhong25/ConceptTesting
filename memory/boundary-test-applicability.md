---
name: boundary-test-applicability
description: Boundary applicability research distinguishes ordered boundaries, joint feasibility, oracle, and slide-specific 4n+1 assumptions
metadata:
  type: reference
---

2026-11-05 usercontinueafteraudit→stringBVArepairimplementedinplace. parsed_float
template/evaluator/inverseconstructor,publicprojectionevidence,nearestinteger
midpointandfixedformatlengthderivations;behaviornotdomain,noautofallback. Schema/
armprotocolv3;oldgenerationcheckpointsincompatible,1375oldartifactbytesunchanged.
205 checksPASS(196 modular+9 development),40 new. ScriptedactualPUT99/124integration
exercisesinjection/globalfreeze/correctedoracle/tworepeatsandfindsknownbugs;
notfreshLLMselection/efficacy. Offline44projection99,derivedguards99/124.0new
model/benchmarkcalls. Reportfinal/review/boundary_string_repair_2026-11-05.md.
Task83resourceboundary993notaddedassemanticthreshold. Supervisorreportunchanged.

2026-11-05 userasksactualboundary-witnessfeasibilityforall44PUTs;CPUauditDONE.
15,691public-spec/contract/PUT-derivedcandidatesfrozen,15,575novelvalid,0LLM/
hiddeninputs. Confirmedsemanticboundarybugs99(negativehalf-integer rounding)
and124(yearwidth3/4/5);83/PUT2RecursionErrorat993(992passes),environment/resource
boundary,notsemanticdomainthreshold. Allneighbortripletsstableintwoisolatedruns.
41othersnowitnessinboundedsearch,notcorrectnessproof.1375priorrunartifacts
unchanged. Reportfinal/review/boundary_feasibility_2026-11-05.mdandJSON;rawplan/
screen/repeatsinfinal/out/boundary_witness_audit_20261105. No generatorrepair.
Mechanism:99needsparsednumericcharacteristicbeyondstringlength;124lengthtemplate
alreadyexistsbutLLMmisseslen10entailedbymm-dd-yyyy;83selectedonlybase-covered1/2.
Userclarifiespipeline_statusMDistobesenttosupervisor:academicprose,brief,only
initialpipeline/baseline+BVAapproach,excludeallnewrunresults. Updatedseparately.

2026-11-05 TERMINAL repairedrunCOMPLETE09:51:35UTC;199379exited,44/44results.
Plain840valid novelinputs/2detectedPUTs(99/0,124/0),BVA67/0.99received/1unknown
physicalattempt,178554known tokens;no historyreset.77source/44inputfreezehashes
andindependentresultaggregationPASS. BVA18no_boundary/15generated/3uncertain/
2no_inputs/3invalid_selection/2covered/1invalid_generation;44selection11context
calls. No matchedgainclaim/posthoctuning/newcalls. EarlierRUNNINGnoticessuperseded.
Userrequestsbriefpipeline/baseline/BVAreportusingno-ai-slop;writtenat
final/review/pipeline_status_2026-11-05.md. Initialfullrun1634PUT/169basefail/
1465basepass/1454evaluated/plain78rawdisagreements;originaloracle,cannotcall78
confirmedbugs. DistinguishlaterV11plain72andcurrentboundaryplain2.
Userclarification:samebriefreportmustuseproseparagraphs,coverinitialpipeline
countsandBVAmethodonly;omitnewboundaryrunresults. MDupdatedaccordingly.

2026-11-04 research requested by user completed; detailed evidence and page
references in `final/review/boundary_applicability_2026-11-04.md`.

Read test_slides functional-testing pp.5–17, official ISTQB CTFL4.0.1 §4.2.2,
Python nextafter documentation, and existing formal-contract paper pp.3–5.
Separate boundary identification, feasible input construction, and oracle verdict.
Independence/single-fault are assumptions supporting one-at-a-time 4n+1, not
universal BVA prerequisites. Joint constraints require feasible witnesses; no
finite global max required; generation caps are not semantic boundaries.

Follow-up clarifies reusable families classify input characteristics, not raw
types: ordered scalar, length/cardinality, position, ordered enum, relational
aggregate. Report now distinguishes type-derived candidates, contract-grounded
obligations and feasible witnesses; schemas/formal types may supply the contract,
so natural-language inference is not always necessary. Taxonomy is synthesis.

Current development_groups boundary fit uses manual label plus base-pass only;
it does not establish verified boundary witnesses or base gaps. Research report
contains the evidence checklist and its sources.

User subsequently authorized implementation on2026-11-04. Standalone per-PUT
`final/modular/boundary_value_analysis/` now implements the requested flow:
saved input types/signatures→templates→LLM boundary/domain selection→LLM inputs.
No templates means0calls; no boundary means1call; successful generation uses2.
Explicit unsupported/invalid/no-input states, immutable checkpoints and read-only
replay; no default-arm integration.41engineering checks pass; offline6PUT smoke
extraction succeeds with0rejected observations. No live LLM/PUT/reference calls.

Initial templates: numeric value,length,numeric elements,sum; threshold may use
another input value/length/sum. Validate quote presence,signature/literals,exact
boundary target and duplicates. LLM prose constraints remain unverified and need
external domain/reference checks. See module README/CHANGELOG/PREREG before runs.
No paper reproduction,benchmark launch,commit or push in this implementation.

Next user request on2026-11-04 integrates module into `BenchmarkPipeline` through
opt-in `BoundaryArm`/`--arms boundary`. Task budget split equally over eligible
visible PUTs,no redistribution;merge/dedup,then existing freeze/reference/evaluation.
Report task/PUT skip statuses and both logical call phases;not call-matched to plain.
Boundary-only bypasses CFG/DFG/witness sampling;empty suites avoid native execution.
CLI now has --task-ids,--target-programs,--input-budget for saved smoke cohorts.
Fullmodular85checks pass (41module+11integration+33existing),with tiny synthetic
sandbox fixtures only;no live model/cohort benchmark. Default arms remain unchanged.

Latest user steering2026-11-04 supersedes default-flow statements above: remove
initial concept-generation steps from the main pipeline and inject input generation
using dependency inversion. Main `BenchmarkPipeline(input_generator=...)` depends
on `generators.InputGenerator`; `MethodInputGenerator` composes any method/stage
returning input batches, without ExperimentArm inheritance or concept packets.
Modern default is plain only; plain/boundary have no legacy concept/witness steps.
Old flow remains in explicit `LegacyArmInputGenerator`, CLI --legacy-generation.
Shared output contract feeds existing freeze/reference/evaluation. Source/config
identity includes the generator. New default outputs:final/out/modular_pipeline.

Validation extracted into named response/input/task-binding functions, with
VALIDATION START/END comments at calls and API/cache/reference checks; checks stay
enabled. Fullmodular93checks passed; custom stage/producer injection, no-model/
no-packet flow, checkpoint/replay and old fixtures covered. No live benchmark.
Read final/modular/generators/README.md for the current API and code examples.

2026-11-05 user requests actual plain+BVA run on the direction-specific dataset.
Prepared/froze existing boundary smoke6PUT (HumanEval0,5,18,81,99,120;PUT0each),
input20/arm/task,target1,expectedQwen27/context8192,max18logicalcalls.60targeted
checks pass;67sourcefiles and source cohort hashes frozen. Registration appended
before any inference. Run directory:final/out/boundary_smoke_plain_bva_20261105;
review report:final/review/boundary_smoke_run_2026-11-05.md.
Endpoint models404;asked user for current endpoint. No controller/completion/
task input/reference result yet. Prepared launch.sh uses private runtime env
outside repo. Do not claim running or substitute a paid backend.

2026-11-05 user supplies new Qwen27endpoint and authorizes run after adding input
execution cache,with autonomous error fixes. Endpoint metadata8192/tokenizer13
verified.112modularchecks pass;cache amendment registered before benchmark calls.
Archived0completion readiness artifacts,refroze68sourcefiles+cache config;source
cohort/settings unchanged. Detached controller156764RUNNING,statusrunning and
HumanEval0/plain attempt1started verified. No scored outcome yet. Same output
directory and6PUT smoke. See [[input-execution-cache]];do not duplicate launch.

2026-11-05 TERMINAL COMPLETE supersedes running:6/6tasks scored,controller156764
finished. Plain80valid novelinputs/0detectedPUTs;BVA19/0.16requests/responses,
0unknown/0retries,32785tokens (plain6calls9043;BVA6selection11382+4construction
12360). BVA statuses:3generated,2no_boundary,1no_inputs. Task0all20BVAproposals
miss exactfloat-adjacentboundary;plain81scalar-vs-list and99missing singleton
tuplecomma lose40inputs. No method repair/extra generation in this frozen run.
Tiny smoke does not show efficacy or prove6PUTs correct. Coldcache428executions/
4hits;warmaudit432hits/0nativecalls,fullread-only replay and68source/6inputhashes
verified. Detailed results:final/review/boundary_smoke_run_2026-11-05.md.

2026-11-05 user scope correction:run the dataset from final/development_groups.py,
not merely smoke6. Actual --groupboundary --tierall export has44tasks/44selected
PUTs. Frozennewrun final/out/boundary_all_plain_bva_20261105;6generation tasks/
16requests imported after exactidentity checks,122files;38fresh tasks remain.
Same BVA/plain methods/config,existingnativecache;no method tuning. Currentprivate
endpointmodels404. Detachedsupervisor168654alive/waiting_endpoint,polls60seconds,
no newcontroller/completion. See [[four-course-development-groups]] and
final/review/boundary_all_run_2026-11-05.md. Do not count imported6asfreshprogress.

2026-11-05 latest: refreshed userendpoint verifiedQwen27/context8192/tokenizer13.
All44boundarygroup now RUNNINGdetachedcontroller170173,supervisor168654;
freshHumanEval2/plainrequeststarted verified.68sources unchanged;6inputtaskfiles
imported,not fresh. User explicitly wants background execution;no all44resultyet.

2026-11-05 all44TERMINAL COMPLETE:plain595validinputs/3PUTs vsBVA121/3PUTs.
Both44/122;plainonly97;BVAonly140;union4. BVA21generated/17no_boundary/
5no_inputs/1invalid_selection.114receivedrequests,0unknown(16imported/98fresh),
187202known tokens incl32785imported. Cache486hits/2692executions of3178records.
44inputfreeze and68sourcehashesverified,no drift;controllers exited0. No matched
call/yield efficacyclaim. Report:final/review/boundary_all_run_2026-11-05.md.

2026-11-05 postrununique-caseaudit:97plain-onlyand140BVA-onlyarebothfalsealarms
from originalHumanEvalreference,correctedHumanEval+agreesPUTin2repeats/case.
140plainalreadyproposedtwospaces,butmalformedargslosesall20records;BVAwholelen
bindingalsodiffersfromspace-runcount. Raw3vs3notconfirmedbugcounts;44/122not
audited. No source/oracle/result changes. See [[reference-oracle-bugs]].

Latest2026-11-05 userauthorizesoraclefix:correctedHumanEval+v0.1.10defaultmodern,
model-free44taskrescore COMPLETE0vs0PUTs;595/121validinputsunchanged,original1336
artifacts/freezeunchanged,0newLLMcalls.122checks/fullreplaypass. Priorraw3vs3are
referencefalsealarms. Then user asks check/propose improving boundary;plan only.
Mechanismaudit:473records→121retained,272targetmiss/41format/21side/18duplicate;
17no_boundary,5no_inputs,1invalidselection. See [[reference-oracle-bugs]] and
final/review/boundary_improvement_plan_2026-11-05.md. No newBVAimplementation/run.

**How to apply:** consult the report before claiming boundary-ready or boundary
coverage; distinguish input boundary coverage from assertions and bug detection.

2026-11-05 latest usersteering:fix BVA after proposal,not another benchmark run.
Implemented compiled targets/named context default,shared CallBuilder for plain/
BVA,run/range/extrema operators,public guard hints,domain-role checks,binding
evidence,obligation quotas and closed-scalar/base-duplicate skipping. Literal
compatibility retained.165checks pass incl34new cases;offline49recheck43structural
passes/6blocked,not semantic precision. Original1336artifacts unchanged;0new live
model/benchmark calls. Report:final/review/boundary_repair_2026-11-05.md. Need fresh
run output for this changed protocol;do not resume old generation checkpoints.

2026-11-05 user explicitly requests live run after repairs,supplies currentprivate
endpoint. Newrun final/out/boundary_all_plain_bva_compiled_20261105 usesall44tasks,
freshplain/BVA generation,namedcodec/compiledtargets,correctedHumanEval+v0.1.10,
sharednativecache,input20perarm/task,max132logicalcalls.165checks/type/ref44pass;
77source/datafilesfrozen.Qwen27/context8192/tokenizer13verified. Detachedcontroller
199379RUNNING;task0/plainfreshresponse received(20namedrecords/1959tokens),BVA
selectionstarted. No resultyet;do not duplicate or import old literal generation.
Report:final/review/boundary_compiled_run_2026-11-05.md.

2026-11-05 09:07UTC livecheck:199379alive,7/44inputbatches,task20eighthinprogress,
15freshresponses.1plain/task10RemoteDisconnectedunknownusage preserved;bounded
retry succeeded.77source/datahashesmatch,noengineeringcrash. BVA compiledscalar
path generated2inputs;4no_boundary/2generated/1uncertain among7completedtasks.
No oracle/PUTscoreyet;generationcountsarenotvalidity/efficacy. Do not duplicate.

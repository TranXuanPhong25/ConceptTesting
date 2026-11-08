---
name: bva-full-humaneval
description: COMPLETE full164soft BVA;1449valid novel inputs,61detected PUTs/22tasks,46value-mismatch PUTs;replay/hashPASS
metadata:
  type: project
---

2026-11-08 cached-naive comparison COMPLETE; worker297867and reporter320170have
exited. All164tasks/1454same base-pass targets scored with BVA's frozen original
full2repeat scorer/3stimeout. Source/input hashes and immutable replay PASS;
0new model calls, no raw-response/schema/literal repairs. Frozen plain source:
v11_concept_inputs,156responses/2481admitted records;31empty generated batches
and task160source resource skip retained. Sealed44baseline untouched.

Report:final/review/naive_vs_soft_bva_full164_2026-11-08.{md,json}.
Output:final/out/naive_vs_soft_bva_full164_20261108_000951/evaluation.
BVA61PUTs/22tasks/1449valid inputs;naive44PUTs/16tasks/1536valid inputs.
Shared31,BVA-only30,naive-only13,union74,netBVA+17. Historical-common1437target
counts identical;the17oldresource omissions change neither detection set.
Stable wrong-value witnesses:BVA46vsnaive17;non-timeout witnesses51vs28.
Old naive72/18used the old oracle/runtime and is not the current comparator.

Critical interpretation:ALL30BVA-only PUTs are on tasks where naive retains ZERO
valid novel input:17lose all source inputs at parser,13lose all admitted inputs
at oracle/domain binding. The latter are tasks40/43/126/151with wrong list/args
packing. On82tasks where both have novel valid inputs,BVA31vsnaive44(noBVA-only).
Preregistered secondary uniform valid-budget expected detections31.00vs32.39;
75eligible tasks have zero matched budget and contribute0. This is descriptive,
not an executed new trial or evidence of better boundary selection. Raw BVA gain
is upstream coverage/interface dependent;do not equate it to semantic superiority.
Writer costs also differ:BVA1454received/1,423,485known tokens vsnaive156/385,522;
historical unknown attempts2vs1separate. Schemas,visibility and epochs differ.
396tests passed before launch;3comparator tests passed separately and again after
report formatting. New helpers/reports/PREREG remain uncommitted;no active job,
new inference, automatic input repair or further benchmark needed.

TERMINAL COMPLETE2026-11-07 supersedes all ACTIVE notices below. Evaluation-only
workerPID192257finished,workerlockreleased,all164task results.157eligible tasks,
1454base-passPUTs,1449novel valid inputs,61confirmed detected PUTs across22tasks.
46PUTs have stable value-mismatch witnesses;15detected PUTs have no stable value
mismatch (exceptions/timeouts). Overlapping per-kind counts:value46,error5,
timeout11,mixed0.7explicit cohort skips unchanged.0eligible tasks have no valid
novel input. Reference filtering15domain/reference rejects+20base duplicates.

Original full2repeat scorer/3stimeout retained. Exact global input freeze equals
source;all1454generation response hashes match;immutable read-only replay passed.
Evaluation-only phase made0model calls. Canonical generation1454received plus
2historical unknown transport attempts;known tokens1,423,485(1,311,541prompt+
111,944completion),493imported calls counted once. Keepalive costs are separate.
No sandbox spawn retry consumed in the evaluation-only job. All earlier stopped
outputs/cached observations remain unchanged;no active benchmark worker or restart
needed. Current root's conditional-confirmation optimization was not used here.

Reports:final/review/boundary_soft_humaneval164_results_2026-11-07.{md,json} and
boundary_soft_full164_generation_2026-11-07.{md,json}. Final primaryoutput:
final/out/boundary_soft_humaneval164_evaluation_20261107_224720.
Generation:final/out/boundary_soft_humaneval164_resume_20261107_195417.
Generation before oracle:3034encoded calls→1550cross-PUT duplicate rejects→1484
retained;51.1%ofencoded calls repeat another PUT's proposal.44invalid-generation,
8no-input PUT records;1402generated. No unique value lost by dedup itself, but
fixed2–3input/PUT shares leave unused diversity budget.20input/task policy differs
from earlier one-PUT20input diagnostic. No matched plain or held-out efficacy
claim;true bug population unknown,so61/1454is not bug recall. Full result/report
and this terminal audit remain uncommitted until user asks.

Latest status supersedes generation-running notices below. Full generation
finished1454responses/164input batches/global freeze. PID103140then stopped at
33task results while spawning bwrap for task33;errorFileNotFoundError occurred
before PUT execution,not a detected bug. Binary exists now;exact transient cause
unestablished. Old generation/output/checkpoints preserved,0LLMresponses retried.

Evaluation-only continuation is ACTIVE PID192257 at
final/out/boundary_soft_humaneval164_evaluation_20261107_224720.
Controllerfinal/src/audits/continue_bva_evaluation.py copied as readonlycontrol.py;
imports original runtime/scorer/worker from source run'sruntime/. No model backend,
endpoint dependency or keepalive. Validates164source input hashes,restores original
visibility packets,imports33complete task/reference/PUT checkpoints and shares
the same input execution cache. Original full2repeat policy/3stimeout retained.
PATHis pinned toos.defpath;detached cold sandbox smoke passed with/bin/bwrapSHA
33516b9cd1fa6432307ad71f23765fa30604b0a8d769dac0d2ba054e85aeec83.
4evaluation-continuation tests passed. Latest actual progress44/164evaluated,
0newmodelattempts,worker running,past failing task33,no sandbox retry consumed.
Allows only1recorded infrastructure-only retry for the same spawn error after
a passing smoke;all other failures stop. One-shot worker:no duplicate controller.
Automatic exact input-freeze comparison and immutable replay on completion.
New code/tests/PREREG for this repair remain uncommitted;main soft unchanged.

User continue audit2026-11-07:PID103140running/lockheld,150of164input tasks,
1346received responses,0evaluation,no global input freeze yet. Frozen runtime,
archive and imported checkpoint hashes all match;no restart or repeated calls.
Pre-reference quality sample on143completed eligible batches:1340encoded inputs
retained,1432cross-PUT duplicates rejected,35invalid-generation and8no-input PUT
records. These are partial generation metrics,not domain-valid input/detection
counts. Leave registered prompts/budgets unchanged;worker auto-freezes all164
batches before reference evaluation and terminal replay/report.

Latest user check2026-11-07: resumedPID103140alive/workerlockheld/statusrunning.
1031received total(538new after493imports),112/164input batches(last111),
0evaluation. Only2unreceived ledgers are the historical archived connection
failures;no new unresolved attempt at this audit. Endpoint models200(expected
Qwen27),1tokencompletion200(5.31s). No restart or runtime/source change.

Latest continuation supersedes stopped-only notices below. Original run remains
interrupted;new output is
final/out/boundary_soft_humaneval164_resume_20261107_195417,PID103140ACTIVE.
Restored original frozen generator/scorer/worker under its runtime/with-P and
isolatedPYTHONPATH;current worktree edits,including separately approved
conditional PUT confirmation,remain untouched. Original registered full2repeat
policy is retained for this continuation. Import probe verifies frozen module
paths;4recoverytests and a0model-call native/replay smoke pass.

Imported493received calls,2historical unknown attempt folders and52completed
input/packet batches,with exact request/content checks. Original stopped output
verified byte-for-byte unchanged.961newlogical calls remained at launch under
original1454cap. Latest actual audit:525received total(32new),56/164input batches,
0evaluation,statusrunning/PIDalive. No retry reset,semantic repair or changed
sampling/budget. Helper:final/src/audits/resume_bva_full.py. Inspect new status/
progress/runner.log before acting;never duplicate either one-shot worker.
Old keepalive receipts remain in parent run and must be counted separately from
new keepalive receipts in any cumulative cost audit.

2026-11-07 latest audit supersedes ACTIVE notices below: PID78543has exited.
status.json state=interrupted,RuntimeError reports frozen put_evaluation.py
changed. This followed the user-requested explanatory comment edit in that file;
Codex acknowledged the missed live-source constraint to the user. Last durable
progress52/164inputtasks(task51),0evaluated. No checkpoints/results were deleted,
no guard/snapshot rewritten and no controller restarted. Keep original source
archive and request ledgers; any continuation must explicitly handle the frozen
source identity and bounded recovery rather than rerunning completions blindly.
User then approves conditional PUT confirmation for current code; this does not
automatically change or resume the interrupted full run's registered protocol.

2026-11-07 user requests BVA on full HumanEval. Launched active soft-bva-v1only
against original frozen qwen35_27b_humaneval164cohort; no PUT generation, plain
regeneration, legacy selector, precision tool or concept requests. Optional budget
question had no override before launch, so existing20input/task configuration is
retained, equally split over visible base-pass PUTs. Cohort1634generated/1465pass;
164requested tasks,157eligible/1454PUTs and at most1454logical calls.32/136skip
shortfall;65/127/132/145/163skip no_base_pass. No old V11-specific exclusions.

Output:final/out/boundary_soft_humaneval164_20261107_171955.
Detached PID78543,worker lock held,statusrunning. Metadata exactQwen27/context8192
and tokenizer13PASS; first real received response observed (2attempts/1response
at initial audit).368modular/development tests PASS before launch. No final result
yet. Always inspect status/progress/PID/lock and actual response counts before
reporting or acting. Do not duplicate/restart the one-shot worker or reset ledgers.

Controller:final/src/audits/run_bva_full.py. Exact request hashes, executed-source/
data/cohort guards,source_archive copies,recorded bounded transport and20mkeepalive.
Progress inprogress.json/stage_events.jsonl;logrunner.log. All164input batches
freeze before corrected reference/domain/native evaluation.3s/input,two repeats,
execution cache. Automatic immutable read-only replay and result_digest.json on
completion. Keepalive is stopped before final summary accounting. On exception,
statusinterrupted; no automatic restart. Source/endpoint failures need diagnosis,
not blind regeneration. Private endpoint stays outside repo and never in memory.

Production code/data and request plan are frozen. Test files and unrelated audit
scripts are outside runtime guards. Preregistration is archived rather than
locking later note edits. Do not edit executed source while active. Full pipeline
multi-PUT calls/budget differ from historical plain; no matched efficacy claim.

Latest user "check" audit2026-11-07:PID78543alive/worker lock held,statusrunning.
52/164input-generation task records complete (last51),487received responses,
487per-PUT results,0evaluation tasks.490attempt ledgers comprise487received,
2archived OpenAIConnectionError unknown attempts (17/3,19/7) and1active52/5call;
do not interpret all3unreceived ledgers as current failures. Current private
endpoint /models200(expectedQwen27)and1tokencompletion200(4.79s). No restart,
source change or scoring performed in this check.

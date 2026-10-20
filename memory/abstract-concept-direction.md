---
name: abstract-concept-direction
description: User wants abstract behavioral concepts using control/state/symbolic summaries and pseudocode; current request is planning only
metadata:
  type: feedback
---

2026-10-14: User asked for concepts more abstract than code facts, suggesting control flow,
symbolic execution and pseudocode, then explicitly said “m lên plan”.

**Why:** existing AST labels and edge rendering do not establish semantic concept guidance.
**How to apply:** follow [PLAN_ABSTRACT_CONCEPTS.md](../trickcatcher_linefacts/PLAN_ABSTRACT_CONCEPTS.md):
behavioral IR and pseudocode, semantic obligation instances, optional bounded solver discovery,
separate abstraction/concept comparisons with tool controls. This turn authorizes a plan;
implementation and new benchmark runs have not started. Existing authorized jobs continue.

User then identified the hard step: how pseudocode yields explicit reasoning about a code weakness.
Plan §3.1 now specifies operation/spec requirements, actual path guarantees, a missing implication,
feasible distinguishing conditions and predicted output/exception. Bindings/derivations must have
source/IR/spec evidence; prose alone is not proof. Still a plan, no new implementation or run.

User further explored MCTS/search over flow contexts and asked about complex temporal/membership/containment
rules, especially equality vs inclusion. Plan now has §§3.2/4.1 and a primary-source research note.
Keep typed predicates/context, distinguish node from constrained state, and never prune solely on LM scores.
Observable tool-controlled reasoning is not white-box access to model internals. Still design only; no paper
reproduction or new agent/MCTS implementation authorized or started.

Plan §4.2 records the distinction between finite terminating executions and an unbounded family of
inputs/traces, fixed mutation grammar vs all values, bounded completeness and inductive loop summaries.
Do not infer global node correctness or completeness from finite source code or one representative case.

User proposed finite state machines. Plan §4.3 prefers finite predicate abstraction for behavioral IR:
state=(location, concept-related predicate valuation, obligation monitor), separate implementation
transitions from spec monitor, concretize/replay/refine mismatch candidates. EFSM with unbounded raw
variables is not automatically finite-state. This remains a design candidate, not implemented FSM/model checking.

User then asked about mutating spec and deleting/moving nodes (filter/check/if). Plan §4.4 defines
finite typed spec/model mutation operators and distinguishing tests. Always distinguish whether the
model comes from normative spec or current PUT; mutant-vs-PUT differences alone do not establish a bug.
No implementation or paper reproduction started. Research note records established NIST prior work.

User requested a consolidated direction/research/proposal summary for confirmation. One-page-ish review:
[DIRECTION_ABSTRACT_CONCEPTS.md](../trickcatcher_linefacts/DIRECTION_ABSTRACT_CONCEPTS.md). It distinguishes
user goals, preferred proposal, feasibility findings and unanswered empirical questions. No assumption
that the user has confirmed implementing FSM/MCTS; no new v16 run started.


2026-10-15: user overrides waiting (“thôi, m làm luôn đi”), authorizes implementation now.
Benchmark-watch timer disabled, other research unchanged. CPU foundation implemented in
v16_behavior_compact after separate v16_behavior IPC-failure copy: representation gate 17/20,
26 tests pass, 0 model calls. See RESULTS §11.48 and pipeline CPU_VALIDATION.md. This is observed
state projection plus implementation-origin mutants, not complete symbolic/FSM or full spec
mutation. Qwen endpoint model check HTTP 404; new endpoint requested through pending question.
Next: same frozen-source proposal gate (2 calls/task), only then conditional seven-arm experiment.
Do not represent candidate/generation or unrun extensions as finished results.

Final active copy is **v16_behavior_ready**: strict malformed JSON rejection added before any
model output, new source freeze/CPU audit 17/20, 29 tests, adapter 10/10. Earlier two copies
preserved. Continue ready `behavior_experiment all --online --workers 2` with live user endpoint.


2026-10-15 ~10:00: user says continue; GPU expected in 10 minutes. Detached single-instance waiter
running (PID in trickcatcher_linefacts/out/runlogs_v16_ready/waiter.pid), no benchmark dependency.
First model metadata check 10:10:40 +0700, then every minute for 40 minutes; existing provided endpoint
is inherited in memory only. Live pinned Qwen triggers unchanged ready `all --online --workers 2`
with dedicated v4 Python. Concept gate >=10/20; no gate relaxation. Completion/failure queues a
follow-up into this same thread. Read status.json/pipeline.log in the runlog directory. If user supplies
a different endpoint, replace only this owned waiter/environment; do not persist endpoint or edit frozen
method. Wrapper source: analysis/run_behavior_when_ready.py. No GPU completion request yet at launch.


2026-10-15 GPU proposal run finished: **v16_behavior_ready concept gate 0/20**, required 10.
6 quote/schema candidate obligations (51:5, 152:1), zero cards. 40 successful new completion requests,
3 exact cache hits, 35,582/23,251 input/output tokens. Initialization signal error fixed via external
main-thread preload adapter, frozen source hashes unchanged. Generation intentionally stopped;
D_IO unmeasured. Read RESULTS §11.49 and analysis/v16_behavior_gate_results.md/json. Do not resume
this version's generation or relax the gate. Next design requires a new registered copy; DSL is too
limited for many requirements and schema/quote/binding failures cascade. This does not test concept
advantage. GPU waiter/resume ended; benchmark-watch remains disabled.


2026-10-15 user “tiếp đi”: implemented v17_templates in new folder, template compiler + semantic
spec-model alternatives, full base verification and computed/replayed discriminator. 44 tests,
representation17/20; proposal gate **2/20** failed (tasks27/78), 40 new requests, 38891/4116 tokens.
Accepted rationale audit is poor: one copies prompt placeholders, the other is unsupported. No
v17 generation or D_IO. Read RESULTS §11.50 and analysis/v17_template_results.md/json.
Separate predeclared six synthetic interface cases (12 new requests,9364/370 tokens): choosing supplied
models6/6; parameter synthesis matches examples4/6, full schema+correctness1/6. Do not generalize this
tiny probe to benchmark success. Next proposed direction: tool-built/base-filtered candidates and
LLM selection/ranking, tool-generated flow/evidence, not free-form parameter/rationale synthesis.
No v18 implementation/run. Current v17/probe finished, frozen sources verified. A queued controller
completion notice may arrive; results are already reported, do not restart generation or duplicate runs.


2026-10-15 user explicitly: MCTS was only a question, not a requirement; omit it. Authorized v18
ID-only selection pilot, now complete. New v18_modelselect copied v17,52 tests,representation17/20,
13/20 nonempty base-consistent menus, canonical audit finds12/20 sampled-consistent retained/displayed
requirements. LLM11 vs lexical-rule12 vs uniform expected9.17, paired0/1: selection gain not shown.
703 frozen valid inputs;119 candidate-property discrepancies confirmed across12 tasks,0 observed
false alarms. Not119 bugs, not D_IO; one selected tuple-component property, task91 not fully consistent.
Task56 LLM wrongly chooses empty=False, rule chooses empty=True. Task78 mixed str/[] type abstention.
20 new calls,6410/165 tokens, no transport failures/cache hits. Tool-generated source/state/effect
records and frozen-pool alternative checks support bounded hypothesis discrimination (task152 signed
sub59/59; task149 dedup16/16 vs even-index9/16). Read RESULTS §11.52 / analysis/v18_modelselect_results.md.
No generation or v19 run. Future comparison needs new preregistration; no canonical feedback into
this frozen selection run. Controller completion callback may arrive; already reported, do not rerun.

For v18, use `selection_experiment` only. Inherited `behavior_experiment` provides preparation helpers; its old generation CLI is not the registered v18 method.


(Codex, 2026-10-15) User authorized v19 implementation and run: rule-first generation vs behavior-only plus mandatory controls. Registered/frozen, CPU gate passes; launch blocked by offline GPU tunnel, no generation calls or D_IO. See trickcatcher_linefacts/analysis/v19_rulegen_status.md and analysis/run_rulegen.py. Resume unchanged with a live endpoint; do not use v18 canonical audit to replace models.

(Codex, 2026-10-15) User says GPU returns in about10 minutes and authorizes automatic launch. Detached v19 waiter active; metadata every60s, max2h, then unchanged frozen controller. See out/runlogs_v19_rulegen/waiter_status.json and waiter.pid. Do not start a duplicate waiter/controller.

(Codex, 2026-10-15) v19 complete; waiter/controller ended normally, no resume needed. Frozen protocol/generation verified. No concept generation gain; strong format compliance bottleneck. Read RESULTS §11.53 and analysis/v19_rulegen_results.md/json before planning next step. Any extraction/interface change must be a new registered folder; never repair this frozen run. Shared witness costs precede generation and are excluded from incremental totals.

(Codex, 2026-10-15) User challenged code-flow correctness, not just detection/format. Audit shows v19 only AST pseudocode+typed model/fault prompting: FSM not used by guidance, empty source bindings, missing definitions and fixed fault truncation. CPU counterexamples expose dependency-read/support-check defects. See analysis/v19_flow_audit.md/json and RESULTS §11.54. Do not claim a connected semantic/FSM reasoning mechanism was evaluated; fixing extraction alone is insufficient. No pipeline changes/new GPU run authorized in this audit turn.

(Codex, 2026-10-15) User explicitly required plan first, then spawn independent subagent audit before implementation. Completed two plan audits, resolved blockers before code, then repeated independent code audits. Narrow multiplicity CPU increment complete in v20_groundedflow_domainfix; earlier frozen copies preserve failed audits/integration. See PLAN_GROUNDED_FLOW_V20.md, analysis/v20_plan_review.md and v20_cpu_results.md. Final real-task requirements remain unreviewed; no general flow/FSM reasoning, no GPU/D_IO. Guards/loops/derived provenance/normative requirement review still open; audit a new scope before expanding.

(Codex, 2026-10-15, latest steering) User rejects static text/property/effect matching as main semantic alignment. Intended next direction is Qwen prompt chaining: spec obligation extraction → actual code abstraction → Qwen alignment/hypothesis → discriminator → execution feedback. Static tools supply facts/check claims, not choose mismatch through hardcoded property rules or lexical selection. v20 stays verification prototype. See PLAN_QWEN_REASONING_CHAIN.md; independently audit chain plan before implementation, preserve frozen runs.


(2026-10-16) User proposes local CFG/control/data dependencies/path conditions → evidence-backed ranked fault hypotheses → constrained input templates, supplying any discovered fuzz input alongside its concept. Repo audit distinguishes existing flat concept-toolinput (RESULTS §11.1, no demonstrated gain) from v13 hypotheses whose prompts hid witnesses. Full verified semantic hypothesis+trace+witness package remains a proposed extension of Qwen chaining. See trickcatcher_linefacts/analysis/flow_hypothesis_witness_direction_2026-10-16.md; no implementation/model run in this audit.

(Codex, 2026-10-16) Plan-only request completed for Qwen prompt chaining; two independent subagent audits accept final v3. See PLAN_QWEN_REASONING_CHAIN.md and analysis/qwen_chain_plan_review.md. Five calls: requirement, actual behavior, Qwen alignment, direct input tuples, execution-feedback revision. No static semantic matcher; no upstream reconstruction in first pilot. Proposed16-fixture diagnostic then conditional full20, max180 scheduled slots; semantic gate requires independently adjudicated labels, model reviews provisional. Legitimate correct-code terminal outcomes must not be penalized by probe gates. No implementation/GPU/new experiment started this turn.


(2026-10-16, latest steering) User clarifies “m lập plan thôi”, superseding implementation/run intent in this discussion. PLAN_FLOW_HYPOTHESIS_TOOLS.md records concept+hypothesis/input attachments and bounded model-selected tools, with source/spec/path evidence, controls and staged review. Future implementation must first copy best pipeline v7 into a new folder with parent hashes/CHANGELOG. No v21 folder, implementation or model run started. Endpoint is not needed for this planning task.

(Codex, 2026-10-16) Scheduled implementation completed only v21_qwenchain offline adapter/interface phase. See [[qwen-chain-offline]], analysis/v21_offline_interfaces.md and local final snapshot; no real Qwen run or semantic claim. Later P2/model/GPU remains unrequested/unrun.

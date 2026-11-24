# Structural refactor,2026-11-01 — no new experiment

User requests one module per run type and one class per pipeline stage, with an
extensible orchestrator so later stages can be added without editing a dispatcher.
The completed v1/recovery results are the fixed behavioral reference. This is a
new folder; no frozen source, prompt, dataset, model, result or checkpoint changes.

Use existing low-level CFG/DFG/Hypothesis/sandbox and streaming transport adapters.
Move stage orchestration, arm strategies, parsing, reference selection, evaluation
and reporting into descriptively named classes, with explicit context and shared
ArtifactStore. Stage dependencies are declared; generation of ALL task inputs must
finish/freeze before any oracle evaluation. Frozen cohort loading never calls a
writer. Optional standalone program-generation/base-filter classes exist separately.

Validation: engineering fixtures for new stages/custom stage insertion, exact prompt
and cache identity, frozen-cohort reuse, oracle barrier, outcome/report equivalence,
and read-only behavior. Then replay all completed164tasks without any API or native
PUT execution, compare reconstructed inputs/oracle/results/comparisons to saved
artifacts, and verify original source/cohort/result hashes remain unchanged.
Independent read-only review before replay release. No new model requests, expanded
benchmark, altered scoring, automatic rerun or commit/push authorized by this work.

## Independent review amendments, before all-task replay

Review found cache/safety gaps and they were fixed prospectively:

- Freeze effective tasks, contracts metadata, all shared source dependencies,
  Python/package versions, model/backend identity and custom stage/arm config.
- Historical replay verifies its original source/contracts/environment and exact
  request identity. Missing witnesses must not invoke a sampler or sandbox.
  Read-only stores reject live model adapters and only accept cached calls.
- Reconstruct the complete summary, including writer/tester/observer accounting,
  missing usage footers and all diagnostics; compare full summary equality.
- Persist stage start/complete/error events only on writable runs. No replay writes.
- Witness-only can run without constructing a model/tokenizer. Additional checks
  cover an all-task oracle barrier and configuration/task invalidation before calls.

Independent review cleared architecture and11initial fixture tests; the expanded
fixture suite is run before full164cache replay. Replay creates no new test inputs,
expected outputs or execution outcomes; it verifies the completed experiment.

## Validation outcome

Expanded14fixture checks passed and an additional toolinput-only budget regression
passed. Its fix budgets the empty-toolinput prompt only when no other model arm
contributes a count; default six-arm behavior and witness-only mode stay identical.
Independent final review cleared all15checks. Full164task read-only replay completed
with2296stage events and exact full-summary parity. Original23snapshot hashes match.
No new benchmark generation/scoring was performed; this refactor is now ready.

## 2026-11-01 amendment — V11 concept source, modern inputs-only generator

User explicitly requests this new arm in the existing code, leaves changes
uncommitted for review, and stops the full V11-family run with checkpoints kept.
This amendment precedes any inference or outcome computation for the new arm.

Name: `v11_concept`. Reuse actual original V11 B5/domain mining and native
coverage/mutmut/fuzz/ranking/gates/G-prime/spec fallback through the existing clean
adapter; do not invoke V11 round-one/hybrid/expected-value/test-selection stages.
Use the SAME modern common_prompt, inputs-only JSON response/parser, one logical
test-generation call/task, seeds/temperature/token/input budgets, generation freeze,
reference contracts/tolerance and all-PUT evaluation as the existing modular arms.
Physical retries remain bounded by the existing streaming transport policy.

V11 produces up to3selected facts per PUT. Adapt to shared task-level guidance by
taking at most4cards (like classical), first rank across visible PUTs then the next
rank; deterministic existing prompt-visibility order. Deduplicate exact kind/text,
truncate owner-prefixed text to800characters. Cards reference only visible PUTs.
Translate method-view source line numbers using unchanged AST nodes; ambiguous
locations explicitly remain labeled as V11 view locations. Store original text and
source/fact hashes. Selection never uses reference/PUT evaluation results. These
aggregation/location adaptations must be disclosed; no claim of a literal full
V11 reproduction or newly invented concept taxonomy.

Imported concept bundles are read-only, verified against original raw PUT hash,
rebuilt view, entry/base tests, model, pinned tools and current V11 source hashes.
Read only bundle/program_view/mining/manifest; do not inspect result/oracle files
to choose concepts. Checkpoint imports with provenance. Missing concepts execute
only V11MiningStage and V11FactsStage in the pinned pytrace sandbox; no canonical
source is sent to them. Read-only replay never computes; cache-only explicitly
fails if unavailable. Method preparation failures yield visible empty guidance
for that PUT, not exclusions from the test denominator. Transport/cap/infrastructure
idle errors propagate instead of turning into empty guidance. No semantic retries
beyond V11's own domain-generation rules.

Primary comparison: `v11_concept` vs `plain` with existing task-level matched-valid
input subsets/permutation analysis. Optional classical/placebo comparisons are
secondary. Test budgets are equal; V11 concept preparation can require more
upstream model/native work. Report that work separately, including historical
shared mining requests referenced by imported concepts. Never count the imported
preparation as free or claim total model budgets are matched.

Keep the modern frozen cohort and eligibility/shortfall protocol unchanged:
164records,157eligible tasks/1454evaluated base-pass PUTs with current cohort.
Do not regenerate PUTs. One generated suite/task executes against all retained
base-pass PUTs, as in the modern pipeline. Full-V11 per-owner suites/1465eligible
PUTs and its raw counts are a different protocol, not a causal comparison.

Engineering boundary/provenance/cache tests and historical replay only during
implementation; no new model calls, benchmark input generation/scoring, automatic
launch or commit/push before user review. Full V11 remains user_stopped.

## 2026-11-02 launch authorization

User supplied a refreshed endpoint and explicitly requested RUN. Launch only modern
`plain` + `v11_concept` on all164frozen task records, preserving the registered
157eligible/1454base-pass protocol and4card rank-round-robin selection. No full-V11
restart, PUT regeneration, source-version fork, commit or push. New output data:
`final/out/v11_concept_inputs`. Detached user service, durable lifecycle status,
existing bounded physical retries, checkpoint reuse and separately accounted
20minute keepalive. Default replay remains read-only. Prelaunch metadata/probe
confirmed expected model/context8192; probe17tokens is diagnostic, not arm cost.
Independent read-only review and engineering checks required before first outcome.

## 2026-11-04 user-authorized prospective resource exclusions

User requested inspecting remaining PUTs for task139-like resource blowups and
explicitly selected excluding those programs from BOTH concept preparation and
result evaluation. This supersedes the initially suggested preparation-only skip.

Review181unfinished base-pass PUTs using source/algorithmic resource cost, without
reference outcomes, model generation or executing candidate PUTs. Exclude17:
HumanEval144/PUT9;147/PUT1,2,3,5,6,7,9;150/PUT0,2,3,4,6,7,8,9;160/PUT6.
Reasons/source hashes/spec hashes are frozen in the resource-exclusion plan.
These are prospective likely-cost decisions, not proofs of timeout or incorrectness.
Keep constant-time147/0,4,8 and modular primality150/5. Do not erase/reclassify
previously completed/failed preparations such as task139.

An optional resource-exclusion plan filters task-local programs before concept
extraction; the filtered task context is used by analysis, BOTH arm prompts, witness
sampling and evaluation. Source cohort file remains unchanged. Preserve original
generation count; recompute retained base-pass count. An affected task with zero
retained base passes is explicitly skipped (160). Compare both arms on identical
retained PUTs and report exclusions with source/effective/evaluated denominators.
Original eligible1454basepass minus17exclusions gives1437planned evaluated PUTs,
subject to the existing explicit task skips; source cohort remains1634/1465basepass.

Per-task exclusion markers must precede any task prompt/input/oracle/result and
remain immutable. Refuse retrospective application to a generated task without
the existing same marker. No affected task has a generated packet/input at review.
Hash the exclusion plan in arm/stage config and source dependencies. Update the
existing run's manifest through an audited user-authorized amendment, preserving
the old manifest and all completed artifact hashes; no new source-version folder,
no additional retries or changed sampler/model/oracle/call budgets. Resume only
after independent review and engineering checks; do not restart fullV11.

## 2026-11-04 — BoundaryValueAnalysis implementation, before live inference

User authorizes a separate boundary module in the existing source tree. Flow:
extract input types → candidate templates → LLM selects characteristic/threshold/
constraints or no-boundary → LLM constructs inputs. No-template and no-boundary
exit early; do not substitute plain generation. This is an implementation scope,
not a registered efficacy benchmark or authorization for paid/full-cohort runs.

Per PUT default: max4boundaries, max20input records, two logical LLM calls maximum,
2048completion tokens each, selection temperature0, input temperature0.7,
context8192, seed314159+tasknumber. Shared ModelCalls transport controls physical
retries. Input type evidence uses saved base calls/annotations; no native analysis,
reference code, plus inputs or expected outputs enter prompts. Up to12base examples
are shown; duplicate filtering uses all saved base inputs. Supported initial
characteristics: scalar numeric value, length, numeric elements, sum; relational
thresholds may reference another supported scalar characteristic.

Schema/quote validation is not semantic entailment. Literal/signature/target-hit
checks are not proof of the LLM's prose domain constraints. Preserve unverified
domain labels and require external contract/reference validation before bug scoring.
No solver proof is inferred from failed construction. Persist unsupported,
no-template, no-boundary, invalid, no-input and transport failures separately.

Validation in this change is engineering fixtures and offline extraction on saved
boundary smoke records only. Before a live method comparison, freeze selected
PUTs/model and task-level budgets/controls, account for both LLM calls, obtain the
required independent review, then freeze inputs before any reference outcomes.
The module is not inserted into default arms or the running V11 experiment.

## 2026-11-04 — main-pipeline boundary adapter, before live inference

User requests integration into the main pipeline. Register opt-in `boundary`,
without changing the default six arms or launching an experiment. Use retained
base-passing programs in the shared visibility order. Determine template eligibility
offline; divide the existing per-task input budget equally over eligible visible
PUTs (at most input_budget PUTs), assigning remainder slots in visibility order.
Unallocated PUTs have explicit budget-exhausted/no-template/unsupported statuses.
Do not redistribute an unused share after seeing LLM selection or generation.

Each allocated PUT has at most one selection and one construction logical call.
Deduplicate merged task inputs and namespace concept IDs by owning PUT. All
retained task PUTs are evaluated using the merged suite after the existing global
generation freeze. Keep original domain/oracle validation and per-task denominator;
an empty boundary arm contributes zero inputs/detections with an explicit status,
not an outcome-dependent task exclusion. No ordinary/plain fallback is added.

The input-count budget matches other arms, but logical/physical call budgets do
not match one-call plain. Report descriptive results and both phase counts; do
not automatically add an efficacy comparison claiming call matching. A future
live comparison still needs its model/cohort/cost controls frozen and reviewed.

Boundary-only preparation requires neither classical graph analysis nor witness
sampling. Mixed runs retain requirements of the other selected arms. Empty total
suites skip native oracle/PUT execution. API/CLI support explicit smoke subsets
and target_programs1; default full-cohort settings are unchanged.
Validation: engineering integration fixtures and historical-compatibility tests;
no live model, HumanEval outcome computation or benchmark launch in this change.

## 2026-11-04 — dependency inversion for input generation, no live experiment

User requests moving validation into named functions/marked blocks and removing
the initial concept-generation steps from the main flow. Main orchestration now
accepts InputGenerator; optional preparation is provided by that dependency.
Input-producing methods/stages return batches through MethodInputGenerator, or a
custom generator returns the common task envelope directly. No mandatory concept
packet or native analysis is required. Default generation is plain only; modern
boundary/plain do not execute the former concept/witness stages. Explicit legacy
selection retains archived protocol adapters and source/checkpoints.

Shared format validation precedes inputs.json and the existing all-task generation
freeze. Oracle/domain validation and PUT scoring remain after that freeze, using
the same inputs schema. Generator class/config/helper sources enter the manifest;
old protocol manifests are not silently migrated. New default output directory:
final/out/modular_pipeline. Model/run budget selection and paid authorization are
not changed by this structural refactor; no live run is launched.

Engineering validation includes injectable model-free producers, custom ordinary
input stages, literal/batch rejection before oracle execution, task-wide freeze,
cache identity and read-only replay; old comparison fixtures use legacy_arms()
explicitly. The validation reorganization keeps checks enabled and does not claim
that schema/quote validation proves LLM semantic constraints.

## 2026-11-05 — user-authorized plain vs BVA boundary smoke run

User explicitly asks to run plain and BVA on the direction-specific dataset
already prepared. Start with the existing boundary smoke tier, following the
saved small-group development protocol: HumanEval0,5,18,81,99,120, PUT0each.
Do not regenerate PUTs, alter sources, replace representatives, expand the tier
or select by reference/plus outcomes. Existing subset selection is outcome-blind.
Selection file: final/out/development_groups/boundary/smoke/selection.json.
Subset cohort_sha256:
3dce7e980e164f6e161febc08455f0ade571a921297e1755d61a42563cdbccfa.
Parent cohort_sha256:
2a32bae531c339f2e403d748984ce5775734bdd8fd0fc9a02620392fbc23c7ed.

Output: final/out/boundary_smoke_plain_bva_20261105. Arms plain,boundary;
target_programs1;input_budget20perarm/pertask;input_tokens2048;input_temperature0.7;
input_seed314159+tasknumber;reference_seed271828+tasknumber;timeout3seconds;
reference/evaluation repeated twice;alltaskinputs frozen before oracle execution.
Backend: the existing user-supplied qwen3.5-27b-awq endpoint, context8192. Verify
metadata/tokenizer before launch; no paid router substitution or fallback model.
Endpoint/credentials remain outside the repository and all logs.

BVA: max4boundary proposals/PUT,selection temperature0,max2048completiontokens;
generation temperature0.7,max2048completiontokens. At most6plain+6selection+
6construction logicalcalls=18. Each logical request retains the existing at-most3
physicalcompletionattempt policy, no reset on resume. The existing20minute
keepalive is recorded separately. No semantic retry/repair or plain fallback for
no-boundary/invalid/truncated selections; keep invalid/no-input reasons
in checkpoints. Transport failures propagate and preserve received responses.

This is a6PUT development smoke, not an efficacy/heldout evaluation. Report raw
valid novel inputs and detected PUTs per arm/task, selected boundary counts,
selection/construction/validation failures and known/unknown token/call costs.
Any per-task matched-valid-input comparison is descriptive and must retain zero
budgets; BVA's2logicalcalls/PUT are not call-matched to plain's1call/task.
Use the existing trusted domain/reference oracle; LLM prose constraints are not
independently proved. Preserve all partial/negative/skip outcomes and do not tune
the method after seeing this run's outputs and silently reuse the same run ID.

Prelaunch60targetedengineeringchecks pass. Same-agent read-only readiness review
verified subset hashes/basepass membership,absence of reference data in prompts,
input budgets,skip paths,global freeze,reference/PUT repeats,call accounting and
detached/resumable execution. No independent reviewer was invoked in this turn.
At registration the stored endpoint returns404on/models;0completion requests have
been sent. Ask for the current endpoint and keep readiness artifacts until live.

## 2026-11-05 — input execution cache, before the authorized live smoke run

User asks to cache previously executed inputs and then run plain+BVA with the
newly supplied Qwen27endpoint, authorizing repairs when needed. Add shared
per-input reference/PUT execution caching to the modern pipeline before sending
any benchmark completion. Same cohort, arms, generation settings and input budgets
as the registration above. No generation skip based on hidden/cache outcomes.

Cache policy isolated-input-execution-v1: each missed input/repeat executes in a
fresh existing bwrap sandbox, eliminating dependence on preceding suite inputs or
imported-module mutations. This changes batch isolation granularity and must be
reported; old batched native outcomes are not automatically imported as equivalent
per-input observations. Exact run checkpoint replay remains unchanged. On a cold
cache there may be more sandbox startups; speedup depends on repeated input reuse.

Cache identity includes the full reference/PUT source and context, contract,
entrypoint, seed, timeout, comparison tolerance, expected output for PUT checks,
typed bound input values (including signed zero and dict insertion order),
Python/platform/package/harness identity, executor implementation and the repeat
index. Stability repeats0and1remain independent observations. Cache hit preserves
the observed result and historical duration, not a newly measured runtime.
Timeouts and infrastructure failures are not reused. Corrupt entries are recomputed.
File locks plus SQLite transactions prevent simultaneous duplicate computation.

Default shared store final/out/execution_cache/results.sqlite3; modern API defaults
to a sibling execution_cache directory. Both arms can reuse post-freeze outcomes,
but no generator sees expected outputs or PUT verdicts from the cache. Per-run
execution receipts report hits, misses, executions, uncached outcomes and missing
receipts; read-only replay requires existing run artifacts and never executes on
a missing cache. Legacy generation retains original execution unless changed
explicitly. CLI supports --execution-cache and --no-execution-cache.

Preserve/archive the earlier readiness manifest/config; there are no completion
attempts or generated task inputs in that prepared run. Re-freeze it with the new
cache/source configuration before launch. Engineering cache tests include real
sandbox isolation, cross-run reuse, typed input identity, expected/source/config/
runtime invalidation, independent repeats, corruption repair, concurrency and
no-execution read-only behavior. Results remain descriptive development smoke,
with equal input caps and unequal LLM call counts.

## 2026-11-05 — corrected scope: complete boundary group from development_groups.py

User corrects the earlier smoke-only run and explicitly points to
final/src/development_groups.py. Execute its boundary/tier=all selection rather than
the6PUTsmoke. The script's original manual inventory has47primaryboundarytasks;
44have a ready representative. Tasks65,127,163have no ready representative and
are omitted by the existing selector,not by benchmark results. Export was produced
using the actual CLI: python -m final.src.development_groups export --group boundary
--tier all --output final/out/development_groups/boundary/all.
Verified subset cohort_sha256:
437c5af3e92d4fcbeb9c2c408ad537adbbbd6971a2d68666cba090f72de70885.
Parent cohort remains2a32bae531c339f2e403d748984ce5775734bdd8fd0fc9a02620392fbc23c7ed.

Run directory final/out/boundary_all_plain_bva_20261105. Same exact plain/BVA
implementations,modelqwen3.5-27b-awq/context8192,one selected savedPUT/task,
inputbudget20/arm/task and all generation/reference/cache settings as smoke.
No outcome-based retuning or format/threshold repair. This expansion is the user's
scope correction,not an attempt to salvage the negative smoke result. The group's
check tier is included in all and must no longer be described as untouched check
data for this run. Group selection stays fixed independently of observed outcomes.

The6smoke task/cohort records are byte-equivalent to their corresponding all-group
records. Import their complete generation-only artifacts and16received requests
after source/model/settings/task/cohort/input-freeze checks. Keep per-file hashes
and provenance. Do not regenerate those tasks or import reference/evaluation
artifacts into the generation flow. Shared native cache serves compatible results
only after the new all44taskgeneration freeze. Record imported versus fresh model
costs:16historical logicalcalls,at most114fresh logicalcalls for38newtasks;
no unknown attempt is reset. Overall maximum130logicalcalls given the inherited
two no-boundary construction skips. Existing physicalretrylimit3perlogicalcall
and separately recorded20minute keepalive continue unchanged.

At preparation the supplied endpoint again returns404on/models. A detached waiting
controller may poll models metadata every60seconds,verify expected model/context
and tokenizer,and launch the frozen command once healthy. It must verify the
manifest source hashes and refuse duplicate or already completed controllers.
Private endpoint configuration can be updated outside the repo;never log URL/keys.
No model completion is sent while endpoint is unavailable. No other dataset group
or paid backend is implicitly added to this plain+BVA boundary-group run.

## 2026-11-05 — corrected HumanEval+ oracle, exact-input rescore

User explicitly authorizes switching to corrected HumanEval+ references and
rescoring the existing44boundarytasks without regenerating PUTs/inputs or making
new LLM calls. Source run:final/out/boundary_all_plain_bva_20261105.
New output:final/out/boundary_all_plain_bva_evalplus_v0110_20261105.
Keep the same cohort,task/PUT selection,all generated/rejected input records,
domain contracts,tolerances,seeds,timeouts,two stability repeats and cache policy.
Do not normalize/repair the malformed generated arguments or loosen BVA targets.

Export a reference-only projection of official HumanEval+v0.1.10,upstream dataset
sha25642526ec0e7d5f3ee0b06d6ced98f8c8bae3d76519151bfb3d36f79010645bd7f.
Retain corrected reference source,prompt,contract,atol,and task binding hashes;
exclude all base_input/plus_input/test arrays. Signatures/spec text match all164
original tasks,and existing contract/atol metadata matches exactly. Task115only
relocates math import to module scope. Use the corrected prompt as oracle context,
while keeping the original generation/PUT context and original task records.

Modern pipeline defaults to the pinned HumanEval+reference provider. Archived
legacy runs and synthetic fixtures can explicitly use original-task references.
The provider is evaluated after the global input freeze and does not enter model
prompts or generator metadata. Bind original prompt hash/entrypoint and require
contract/tolerance version agreement;refuse silent fallback on mismatch.

Rescore injects FrozenInputsGenerator,checks original task/cohort/metadata/input
hashes,and has no model backend or tokenizer. New-run model invocation count must
be0;report historical generation cost separately. Cache keys already include full
source/context/expected outputs,so new reference programs and changed expected
values cannot reuse obsolete observations. Preserve old run artifacts/source
cohort and write evaluation results separately. Reference fixes may alter valid
input yield as well as detections;report this directly without selecting cases.

Engineering validation includes all164bindings/compilation,97/140corrected outputs,
115import relocation,source/spec/domain mismatch rejection,frozen-input tamper
checks,separate-output enforcement,zero-model rescoring and complete replay.
Full modular122engineeringchecks pass before benchmark rescoring. Verify the new
generation freeze equals the source freeze,all original artifact bytes unchanged,
and no calls/request attempts were created in the new rescore directory.

## 2026-11-05 — user-authorized BVA engineering repair, no new live run

User's latest steering requests fixing the proposed BVA mechanism. Default now
uses compiled targets and named contexts;plain/BVA share the CallBuilder encoder.
LLM selects typed characteristics/thresholds/roles;code computes exact neighborhoods
and supported shapes. No model expressions,reference outputs or PUT verdicts enter
generation. Keep max4boundaries/max20inputs,seeds,temperatures and token caps.

Public guard hints are bounded;unknown clauses,OR and mutated predicates stay
unknown. Domain roles require recognized necessary evidence;behavior guards are
not preconditions. Context quotas are fixed before outputs,no success-based
redistribution. Closed scalar targets can avoid the second LLM call,with exact
base duplicates removed. Do not skip entire vector contexts based on one base hit.

Literal compatibility remains explicit/tagged. Resource limits1000items/16000chars
are not semantic boundaries. New schema/source requires fresh run artifacts;
keep all prior results unchanged. Cache identity includes shared signature parsing.
165combinedengineeringchecks pass,including34new cases. Offline49proposal audit
is structural diagnostic only,not semantic precision or efficacy. No new live
generation/benchmark is performed by this implementation task.

## 2026-11-05 — user-authorized compiled BVA/plain live run

User now explicitly requests running the repaired methods using the supplied
Qwen3.5-27B-AWQ endpoint. Same boundary/all44selection from development_groups.py,
one saved representative PUT/task,cohort sha256
437c5af3e92d4fcbeb9c2c408ad537adbbbd6971a2d68666cba090f72de70885.
Fresh output:final/out/boundary_all_plain_bva_compiled_20261105.

Arms plain,boundary;modern named-argument encoder shared by both,BVA default
compiled target/context policy. Keep max20inputs/arm/task,max4boundaries/PUT,
selection temperature0,input/context temperature0.7,2048completion tokens per
logicalcall,context8192,input seed314159+tasknumber,reference seed271828+tasknumber,
timeout3seconds,two independent native repeat slots. Maximum132logicalcalls
(44plain+44selection+atmost44context);code-only/scalar/skip paths can reduce this.
No extra model-based semantic repair/fallback requests. Existing max3physical
completion attempts/slot and separately recorded20minute keepalive remain.

All44tasks regenerate method inputs because plain/BVA generation contracts changed;
do not import old literal-generation responses as fresh compiled-method outcomes.
Keep source PUTs,cohort,previous inputs/results unchanged. Shared execution cache
is enabled;it reuses only matching source/context/input/expected/runtime/repeat
identities. Corrected pinned HumanEval+v0.1.10provider is the evaluation oracle;
the global all44inputfreeze precedes reference/PUT execution. No hidden plus inputs
or reference outputs are supplied to generators. Domain/binding unknowns and
resource/constructor failures remain explicit,not automatic task exclusions.

Report each arm's valid yield,task/PUTdetections,selection/construction statuses,
target/format/domain/duplicate rejects,logical/physicalcalls/tokens and nativecache
receipts. Both arms have equal input caps but different request counts;any matched
input-budget analysis is descriptive,not proof of matched-call concept efficacy.
Do not enlarge the dataset or retune after seeing results under this run ID.

165combinedengineeringchecks already pass;prelaunch confirms44reference/spec/
domain bindings,type/template support,model metadata8192and tokenizer13. Freeze
source/data/arm/provider/config hashes before the first request and run detached.
Same-agent readiness review only;no independent agent was invoked in this turn.

## Post-run boundary feasibility audit — 2026-11-05

User asks whether the44selected PUTs actually admit boundary inputs exposing bugs.
This is a post-hoc CPU diagnostic,not a new LLM comparison or a change to either
frozen method. Existing run outputs remain unchanged. No model/hidden-test calls.
Before execution,freeze15,691task-specific candidates across44tasks,derived from
public specs/contracts and inspected PUT source. Bounded grids include scalar and
float-adjacent thresholds,list/string lengths,relational/aggregate transitions,
parsed numeric/date strings,and task83's implementation recursion transition.
Public finite integer domains1..1000are enumerated fully for107and156only.

Use the existing bwrap oracle/evaluator with corrected HumanEval+v0.1.10,3second
per-call timeout,original tolerance/seed. Bulk screening is batched;at most one
representative per failure status per task is replayed twice in fresh isolated
cache slots before claiming a witness. Do not insert batch observations into the
shared isolated-input cache. Exclude base duplicates. Distinguish output mismatch,
functional exception and timeout;resource boundaries are implementation limits,
not automatically semantic BVA thresholds. Reference errors are not PUT bugs.
No witness in this bounded audit does not prove correctness or boundary absence.
Record candidate/output/source hashes and verify original run artifacts unchanged.
This same-agent diagnostic requires no new method promotion or experiment launch.

Dependent confirmation:after the fixed screen,select the planned neighboring
inputs for99(-0.5and its adjacent floats),124(year widths3/4/5),83(992/993/994).
Selection is post-screen;the9records/replaypolicy were saved in audit output
followup_plan.json before their isolated execution. This adds two-repeat local
confirmation of the transition itself,not extra LLM calls or method tuning.

## Development amendment — string-derived BVA characteristics, 2026-11-05

User says continue after the44PUTfeasibilityaudit. Repair the observed missing
characteristic/binding mechanisms in place. Add a parsed_float candidate for
strings,requiring public numeric-string declaration evidence before selection
binding. Compile exact finite float targets back to literal strings;permit the
single-parameter constant-target path to finish without a context LLM call.
Add bounded public-spec derivations for nearest-integer midpoint representatives
and declared fixed-width mask lengths. All inferred format guards are behavior,
not input-domain clauses. Keep the two-call cap,no forced selection/fallback,
and existing freeze/contract/reference/PUT/cache boundary intact.

Use generic rules with no task identifiers,reference code,hidden inputs or
observed failures in production generation. Post-hoc saved PUT99/124fixtures are
engineering regression cases:script the selection/context responses and verify
actual target construction,global freeze and corrected oracle behavior. These
checks are not independent efficacy evidence or fresh model results. Task83's
runtime recursion limit remains a separate resource issue;do not turn993into a
semantic template threshold. Version3source/schema invalidates prior generation
checkpoints;any later model comparison must use a new output directory and its
own prospective run registration. No new LLM benchmark is launched by this repair.


## 2026-11-05 — runtime extraction and removal of obsolete methods

User requests clear naming and deletion of old concept functionality. Extract the
shared executor/worker/contracts and model transport/checkpoint/keepalive into
final/src/runtime. Current modular pipeline exposes only plain/BVA; delete its old
concept methods, stages, adapter and CLI options. Preserve historical experiment
sources/results/checkpoints for provenance, without imports from current modules.

This is an engineering refactor, with no new benchmark/model calls or efficacy
claim. Keep sandbox implementation and generation-freeze/reference/PUT checks.
Use standalone dataset/cohort/domain helpers; record runtime sources in manifest
and cache keys. New protocol input-generation-benchmark-v2 requires fresh output
directories. Do not relax source identity checks to replay old code with new code.
Frozen-input rescore continues to accept exact old saved input records.

Run current integration/cache/reference tests, extracted transport/retry tests and
a dependency test that blocks historical imports. Independent read-only review
will check isolation, preserved behavior and removal completeness.

Read-only review amendment: require a current modular manifest for replay instead
of allowing a missing manifest to bypass identity checks. Add missing-manifest and
old-protocol regressions. Remove stale concept/CFG and matched-comparison wording
from current report text; no benchmark outcomes were computed for this refactor.

## 2026-11-05 — retire concept code and consolidate src/data

User authorizes deleting concept_reference_v1 code after dependency extraction,
then requests final/src and final/data. Remove obsolete original/recovery/V11
concept executable modules, preserving documentation and all final/out results.
Move remaining source into final/src and dataset/domain/reference/inventory data
into final/data. Update imports and entry points; no compatibility forwarding to
retired packages. Shared runtime, current input methods and original plain
baseline remain available under the source package.

Preserve a byte-hash ledger of existing run/checkpoint artifacts. Keep pre-layout
inventory/subset snapshots under data/development_groups/archive. Rebuild the
source-bound development inventory offline using unchanged specs/PUTs/base evidence;
require exact structural/selection equality apart from the builder source hash and
its dependent inventory hash. No model/reference/PUT executions in this rebuild.
Do not rewrite existing run manifests or source hashes to force old runs to resume.

Layout review amendment: preserve the original plain baseline default output at
final/out/humaneval164 and route the moved PUT-quality audit summary explicitly to
final/review/put_quality/SUMMARY.json. Source relocation must not redirect outputs
into src. Both paths corrected before any new baseline/audit execution.

## 2026-11-05 — remove redundant retired files

User requests deleting excess files. Remove retired concept documentation/locks,
original plain baseline executor/pipeline/CLI, obsolete baseline validation files,
and redundant pre-layout inventory snapshots now preserved in Git. Keep current
source/data, research notes/papers, original reports and final/out checkpoints.
Use existing byte-identical runtime contract helpers and retain only the program
writer prompt in modular/program_prompts.py. Port baseline sandbox/parser safety
checks to current runtime; retire tests dedicated to the deleted baseline workflow.
No model/benchmark runs or changes to input-generation/reference semantics.

Independent cleanup review complete: no dangling imports; writer prompt AST and
contract helper bytes match; source manifests retain runtime/prompt identity.
No model/benchmark calls or efficacy claims.

## 2026-11-05 — boundary prompt v4 smoke

User asks to try prompt v4 from final/review/boundary_prompt_v4_proposal_2026-11-05.md.
Protocol: five-step selection worksheet (order, spec/code/edge transitions, alignment,
reach/infect/propagate, selection) and context rules (one factor, reach, propagate).
Schema boundary-value-analysis-4; fresh output final/out/boundary_smoke_prompt_v4_20261105.
Scope: 6 outcome-blind smoke PUTs (HumanEval/0, 5, 18, 81, 99, 120), arm boundary only,
at most 12 logical calls, target_programs 1, input budget 20, corrected references.

Descriptive interface check only: selected boundaries, sides, origins, retained inputs and
rejections. Smoke tasks are development tasks, no plain/placebo comparison, no efficacy claim.
Prompt was written after reading saved cohort failures, so this is not held-out evidence.

Smoke amendment 2026-11-05: output final/out/boundary_smoke_prompt_v4_20261105 finished
6/6, 8 calls, 12 inputs, 1 PUT (HumanEval/99). Tasks 81 and 120 and one boundary of task 0
were lost to invalid_constraint because the v4 example no longer showed the constraint
object. This is a prompt defect, fixed by restoring that shape. Saved artifacts stay as is;
any rerun needs a fresh output directory.

## 2026-11-05 — boundary known-bug diagnostic

User approves running prompt v4 (constraint example fixed) on 10 PUTs from
final/review/boundary_known_bug_tasks_2026-11-05.md. Cohort
final/out/development_groups/boundary/known_bug_10, output
final/out/boundary_known_bug10_prompt_v4_20261105, arm boundary only, target_programs 1,
input budget 20, corrected references, at most 20 logical calls.

PUTs were selected by outcome, so this is diagnostic only: does the generator reach the known
boundary? Report per task selection status, whether the witness boundary was selected, and
detection. No detection rate, plain comparison or efficacy claim. Tasks 16 and 23 are not
expressible with current characteristics and are expected misses.

## 2026-11-05 — boundary selection/context repair (offline only)

User requests fixing the diagnosed selection/context losses. This amendment is
after inspecting the outcome-selected known-bug10 diagnostic. Separate public
domain evidence from code/natural-edge threshold evidence; do not require a spec
rule change for code/edge candidates. Increase default selection tokens to4096
and distinguish length-truncated selection from invalid JSON or no applicability.
Context families may include valid sign extremes, empty/token-only strings and
endpoint placement, with the same family reused across sides within the budget.

Add optional bounded declarative context requirements (palindrome, element signs,
token-only strings), check them on constructed calls, and preserve palindrome
when constructing sums where the supplied shape permits it. Unsupported or unmet
requirements are explicit construction rejections, not feasibility proofs. Prose
reach/propagation and remaining contract constraints stay unverified. Keep the
numeric-string binding guard and existing characteristic coverage unchanged.

Protocol boundary-value-analysis-5 requires fresh artifacts. Validation is offline
engineering tests only: no model calls, diagnostic rerun, benchmark scoring or
new efficacy claim. Historical run outputs remain unchanged.

## 2026-11-05 — protocol5 known-bug10 rerun authorization

User now requests rerunning the repaired method. Same outcome-selected10PUT
cohort and task order as v4, cohort_sha256
274e5251c97682d2d0c43d53fb936a859822737ec3d33f54e05e09aac3eb48c1.
Fresh output:final/out/boundary_known_bug10_prompt_v5_20261105. Boundary only,
target_programs1,input_budget20/task,selection4096/input2048/context8192,
selection temperature0,input temperature0.7,input seed314159+tasknumber,
reference seed271828+tasknumber,timeout3s,two separate native-repeat slots.
Same qwen3.5-27b-awq model via user-supplied endpoint; no paid-provider/model
substitution. At most20logical task calls,existing at-most3physical completion
attempts/slot; no semantic retry or expansion.20minute keepalive separately
recorded. Never log/store endpoint URLs or credentials in repo artifacts.

Corrected pinned HumanEval+v0.1.10 references are used only after all10tasks'
generation freezes. Shared exact execution-cache reuse remains enabled. Compare
per-task selected characteristics, abstentions/truncation, context families,
declared requirement checks, valid inputs, detections and costs with frozenv4.
Both this repair and rerun are post-hoc on these10PUTs; no detection-rate,
call-matched efficacy or held-out generalization claim. No task-specific witness
inputs or known-boundary annotations are supplied to the generator.16/23still
lack character-code characteristics; numeric-string binding guard stays intact.

Pre-inference independent Codex review found two residual contradictions:
candidate metadata still required spec-supported thresholds/spec_evidence;
context propagation still demanded a side_rules difference. Both corrected
before inference so template metadata and context match the selection contract.
Freeze source/data/old-output hashes before launch; keep all original outputs.

## 2026-11-05 — compact selection prompt diagnostic

User approves shortening the prompt and trying the previously discussed semantic
failures on23/72/157. This is a post-hoc diagnostic of prompt compression, not a
new efficacy benchmark or a pure causal test of token length. Prior workload/raw
vs structured diagnostics include v72_diagnosisprobe and the v33 chain comparison;
this experiment changes only the current BVA selection instruction wording.

Replace selection instructions with a shorter version of the same task; keep
system message, task-data object, candidate menu, output schema/example, compiler,
validators and context prompt unchanged. No task-specific byte/character, prefix
sum, polarity or hypotenuse hints/examples are added. Selection budget4096,
generation2048/context8192,input cap20/task,existing seeds/temperatures, same
qwen3.5-27b-awq. Protocol6 records the instruction change; fresh output only:
final/out/boundary_compact_selection3_20261105. At most6logical task calls,
existing max3physical completion attempts/slot, no semantic retries or expansion.
Use exact23/72/157PUTs from the frozen known_bug_10 cohort. No PUT regeneration.

Comparator: saved protocol5 requests/responses on these same3PUTs, not fresh
long-prompt controls. Verify identical task-data objects, system message, model,
budgets and output example before inference. All3generation results freeze before
corrected HumanEval+reference/PUT evaluation. Shared cache and two native repeat
slots remain. Paid-provider substitution is outside this diagnostic scope.

Primary review is semantic, recorded separately from schema validity and detection:
23distinguishes intended string length from implementation byte length; an
unsupported_characteristic response with correct explanation counts as semantic
recognition, not generated-input success.72distinguishes total sum from partial
accumulation rather than alleging an unsupported operator mismatch.157does not
call positive-domain acceptance and nonpositive rejection an operator mismatch;
recognition of the arithmetic/tolerance issue is reported separately. An empty
or vague response is not semantic success. Report exact text and unknowns rather
than forcing a binary judgment when evidence is insufficient.

Secondary: selected boundaries/statuses, valid yield, context properties and native
outcomes, plus actual prompt/completion tokens and known/unknown usage. Three
post-hoc cases and rewritten wording cannot isolate length from salience or
instruction deletion/rephrasing; no efficacy/generalization claim. Independent
read-only review, offline checks and source/prior-output snapshots precede calls.

### 2026-11-06 pre-inference review/control amendment

Independent review confirms exact context instruction/output-example retention
and no task-specific added hints. Selection text5908→3347characters.234modular
tests pass. Review also identifies a historical confound: runtime transport
changed from v5's urllib/SSE to LangChain/OpenAI, alongside pipeline metadata and
input-generation source edits. Thus the historical v5 contrast is not prompt-only.

Before observing any new response, add3fresh long-selection controls using the
exact saved v5 messages/settings on the current backend. Interleave the6selection
calls in task pairs:23long→short,72short→long,157long→short. Both variants keep
the same model/data/menu/system message/output example/budgets/seed/temperature.
Use normal checkpointed calls; cache short selections under their normal call
keys so the subsequent standard BVA pipeline consumes them without new selection
completions. Only the short variant may generate contexts (up to3morecalls), then
all3short results freeze before normal reference/PUT evaluation.

Total cap is now9logical task calls:3long controls +3short selections +atmost3
short contexts, existing max3physical attempts each. This replaces the6call cap;
no additional tasks/repetitions/semantic repair. Current local date is Nov6, so
fresh output is final/out/boundary_compact_selection3_20261106, replacing the
unused planned Nov5output. Long controls live in its long_selection_control/
subdirectory, with separate accounting. Periodic20minute keepalive is separate.
Primary comparison is the fresh pair on the current runtime; historical v5 is
secondary context. This still tests the compression/rephrasing bundle rather
than isolating token length, and remains a post-hoc three-case diagnostic.

## 2026-11-06 — opt-in checked grounding diagnostic after v5 checkpoint

User requests restoring/committing v5then trying the proposed improvements.
Stable checkpoint13d92ee9was pushed to main before this trial. Prior relevant
attempts: v10spec predicates (no gain), v47menu ranking (no gain), v66construction
engineering success/v68no concept gain, v69typedIR without semantic sensitivity.
This is an engineering repair of existing BVA, not a paper reproduction.

Add opt-in grounding_mode=checked; default mode keeps v5instruction bytes and
behavior. Scope: bounded AST facts for quantity identity, builtin string codepoint/
encoded length, simple prefix accumulations and immediate False-return polarity.
Facts state supported syntax/assumptions, not NL entailment or proven bug labels.
Complex/ambiguous mutation, shadowed builtins and unsupported arithmetic remain
unknown. Never execute the PUT to infer intent or query reference during generation.

Recognized necessary scalar type assertions can widen observed-int templates to
float; contracts are not mined from outputs. Prune concrete side targets that
violate recognized guards for that target alone before dividing context budgets.
Other joint constraints are still checked on full calls. Add raw code-point
characteristic (not interchangeable with transformed ord or byte length), with
explicit receipts for transformations. Source-derived context requests describe
supported non-ASCII and proper-prefix-vs-total conditions; requested properties
are checked after construction. Do not fill missing tests using known witnesses.
Do not reject all task inputs just because semantic correspondence is unknown.

First run offline engineering tests and artifact audit of the existing six misses.
After independent review, at most12logical calls for same6PUTs2/11/16/23/72/157,
input20/task,selection4096/context8192,generation2048,seeds/temperatures as v5,
same exact qwen3.5-27b-awq. Fresh output final/out/boundary_checked6_20261106;
no new PUTs, model substitutions, semantic retries or larger cohort. Standard
transport retries remain bounded; all inputs freeze before corrected reference
and native evaluation. Report mechanism changes and unknowns, not detection rate.
Candidate pool/context hints/type repairs all change together; no isolated gain
of semantic ranking versus pool expansion without future matched controls.
Keep experiment uncommitted for review after the stablev5commit; preserve all
previous outputs. Failed readiness/endpoint checks do not authorize retries of
unknown completions beyond the existing recorded policy.

### Checked grounding independent-review amendment (before live diagnostic)

Reviewer found unsupported-syntax false receipts. Fixes were applied before the
offline artifact audit or model calls. This amendment was written just after the
offline audit completed, before inspecting its findings; it is not a prospective
registration of that offline result. Applied conservative unknown handling for nested scopes,
wildcard imports, prior unsupported loops/mutations, annotated/walrus writes and
keyword-offset sum calls. Character-origin aliases are separate from actual ord
results; unsupported operators do not emit code-point comparisons. Type evidence
abstains on shadowed contract type builtins. Added regression cases:44grounding
engineering tests pass. These repairs constrain source receipts; they do not
prove general NL binding. Non-ASCII context goals only derive from recognized
UTF-8 encoding, not arbitrary encodings. Live old endpoint returned404before any
completion; user asked for a new endpoint. Offline trial proceeds independently.

### Checked6 live readiness after endpoint reply

User resent the endpoint; exact qwen3.5-27b-awq metadata/context8192now pass.
278modular tests pass incl44grounding cases, independent review cleared. All6
selection prompts fit with4096output+128reserve; observed prompt tokens range
2273–3463. No source change after these readiness checks. Proceed with the
registered6miss-only diagnostic, max12logical calls, using fresh checked6output.
Capture source/prior-output snapshots and runner hash before launch. No known
witnesses or reference data enter prompts. Keep stablev5commit separate from
these uncommitted trials, and report all capability/pool/guidance confounds.

## 2026-11-06 — GPT-5.6 Luna direct inputs with failure feedback

User explicitly asks to inform exactgpt-5.6-lunaabout the failures and require
immediate input-only output without tools. Scope is the3record-rejection cases
23/72/157, same PUTs7/4/3. One bundled native Codex CLI invocation, model
gpt-5.6-luna/low, no retries/fallback or model substitution. CLI exposes no
enforceable output-token cap; actual usage reported. No Qwen/paid API calls.

Prompt includes only public spec/contract/PUT and prior generated bad records
with validator/arithmetic failure feedback. No corrected-reference outputs,
hidden inputs or known successful witness supplied. Up to20named input calls
per task, no analysis/assertions/selection schema/tool calls. This is an assisted
post-hoc input-construction diagnostic, not a matched model or BVA efficacy test.

Use the existing native Luna client with ephemeral empty cwd, user config/rules
ignored, shell/code-mode host/browser/apps/plugins/subagents disabled, web off.
Tool schemas may remain exposed by the CLI; accept only agent-message/reasoning
events and abort on tool or denied-router attempts. No model-executed tools.
Exact identity is requested CLI-m/local catalog unless server events report it.
Do not use a provider with tools or switch to another Luna/stronger model.

Freeze all3returned batches before reference/native execution. Standard contract,
corrected HumanEval+oracle and two native repeat slots remain evaluation-only.
Use a frozen direct-input producer injected into existing pipeline, not the
working-tree method generator currently edited by another session. Preserve
those edits. Model output schema failures are reported without response repair
or extra LLM calls. Independent pre-inference review precedes the single call.
Fresh output:final/out/boundary_luna_direct3_20261106. Prior checked6outputs
preserved. Return actual accepted inputs and failure reasons, not just counts.

Luna pre-inference review cleared the single call with no blocking changes.
Tool schemas may remain exposed, so report zero observed tool use only after
event/router audit. Exact3task IDs, <=20named calls/task and no extra assertion/
analysis fields are validated before all-batch freeze; no JSON repair/retry.

## 2026-11-06 — naive inputs rescore on exact known_bug10 PUTs

User asks for boundary/naive numbers on these exact10PUTs. Existing naive164
cached labels use a different reference protocol, so rescore its frozen plain
inputs only against current corrected HumanEval+oracle and exact known_bug10
cohort. Zero new model/generation calls. No baseline unsealing/mutation or input
repair/augmentation. Export a source-hashed plain-only10task slice and use the
existing FrozenInputsGenerator+standard pipeline; all10batches freeze before
reference/evaluation. Existing input budget20,timeout3s,seeds,2repeat slots/cache.
Fresh output:final/out/naive_known_bug10_rescore_20261106. Report source-generated
versus valid inputs and detection per exacttask/PUT, alongside boundaryv5.
The original naive prompt saw its historical cohort, so a shared corrected oracle
does not make this a matched-prompt/visibility/call-budget causal comparison.
Outcome-selected10sample remains diagnostic; do not call counts detection rates.

## 2026-11-06 — matched prompt-style diagnostic after user agreement

User agrees with the hypothesis that restrictive scaffolding can constrain the
model's natural exploration. Test on the3previously discussed v5losses2/11/157,
same exactPUTs6/1/3. Prior art in this repo: v33chain/direct showed hard-gate loss;
compact-selection3rewrote instructions but retained the selection schema/gates;
Luna direct3changed model and added failure feedback. This trial removes those
specific confounds for a bounded prompt-style comparison, not a new efficacy study.

Three arms: direct generation; direct with a short nonbinding BVA suggestion;
an adapted five-step v5worksheet applied internally before returning inputs.
All arms use the same public spec/contract, one identical PUT and same existing
base calls, same system message, named-input-only output schema, cap20inputs,
qwen3.5-27b-awq,temperature0.7,seed314159+task,completion2048/context8192.
No alternative PUTs, failure feedback, known witnesses, implementation receipts,
candidate templates/menu, model-provided assertions or reference labels. Only
the instruction-style block differs; no continuation or semantic retry.

Exactly9logical requests in balanced task/arm order:
2direct→soft→worksheet;11soft→worksheet→direct;157worksheet→direct→soft.
Existing max3physical transport attempts/slot retained; unknowns disclosed.
Endpoint metadata/tokenization, read-only review and source/request snapshots
precede inference. Fresh output final/out/boundary_prompt_style3_20261106.

All9outputs freeze before shared corrected-reference/PUT evaluation,2native
repeats and exact execution cache. No target compiler or applicability/selection
gate in any arm. Keep raw generated values unchanged; common CallBuilder/schema/
domain/duplicate checks apply to all. Do not repair malformed/truncated responses.
Use frozen-input producer injection; preserve unrelated method-generator edits.

This compares free/soft/worksheet instruction bundles under one-stage direct
output, not the entire current two-stage BVA pipeline. It cannot isolate prompt
length, information content, latent search randomness or hard-gate effects from
one sample per task/arm. Post-hoc tasks and BVA hints do not support held-out or
general detection-rate claims. Report novel valid yield, per-PUT detection,
actual boundary-related inputs, input diversity and raw response failure modes.
No retuning, extra tasks/repeats, baseline regeneration or default replacement.

Clarification before inference: the3direct-arm calls are fresh matched experimental
controls because their one-PUT/context packet differs from historical naive.
They do not regenerate, unseal or replace the user's fixed44task baseline.
Existing naive9/10PUT prompts cannot serve as identical-context controls here.

Pre-inference independent review confirms exact matched data/system/settings.
Reviewer found a residual unavailable-helper cue in adapted worksheet: removed
the claim that float_adjacent supplies values since no arm has a constructor.
Changed worksheet's "write briefly" to "consider briefly" to keep reasoning
internal and retain the common input-only output contract. No response observed
before these changes; worksheet remains an explicitly adapted instruction arm.

User now explicitly schedules the existing endpoint check/run20minutes later,
expecting server startup then. Scheduled UTC2026-11-06T12:51:15Z
(19:51:15Asia/Ho_Chi_Minh), anchored to the schedule request's clock check.
Detached local controller sleeps until that time, verifies frozen source/requests
and old outputs, checks exact model/context and tokenizes all9requests before
any completion. If any check fails, record blocked state and stop; no model
substitution, automatic rescheduling, source changes or completion retries beyond
the existing per-slot transport policy. On successful readiness, launch the frozen
runner once, supervise terminal status and emit a mechanical result digest.
No completion before due time. Existing fixed baseline and defaultv5unchanged.

Scheduler review amendment before launch: persist exclusive one-shot readiness
and launch reservations before HTTP/Popen. The process lock alone did not cover
crash/restart windows. Consumed reservations stop later automatic restarts;
frozen scheduler/runner/schedule/request source hashes include these fixes.

## 2026-11-07 — prepare executable full10 prompt-style command, no launch

User asks to try all10cases and requests an executable .sh file. Generalize the
matched direct/soft/worksheet runner into final/src/audits/run_prompt_style.py,
with final/run_prompt_style10.sh and exact frozen3task style JSON. Do not launch
from the preparation turn. This extends existing diagnostic, not a new method;
all10known-bugPUTs remain outcome-selected/post-hoc, not held-out efficacy data.

Default:10tasks×3arms=30slots,input20/task/arm,temperature.7,seed314159+task,
completion2048/context8192/exactQwen27. Reuse the9completed3task responses only
when full messages/sampling/budgets/model label match; keep import receipts and
historical token usage separate. Thus21newlogical model calls planned. Explicit
--no-reuse permits30fresh slots when user chooses it; unchanged fixed44baseline
is not regenerated or modified. Reused versus new time epochs/order are disclosed.
No successful-witness selection, response repair, prompt edits or semantic retries.

New output directory per invocation; default shell launches detached and prints
PID/log/status paths. Offline --check-only prepares/checks identity without any
network/model/evaluation calls. Metadata/tokenize allslots before inference;
all30slot outputs freeze before corrected-reference/evaluation and read-only
replay. Existing bounded transport retry policy remains; one-shot worker marker
prevents accidental second controller. All source/request/reused/prior hashes
are bound to the prepared run. Private endpoint stays in external env file.

Verification at preparation:chmod755,bash-n,help and offline full10identitycheck
pass;30prepared/9reused/21newplanned,0modelcalls. Read-only independent review
requested before delivering the runnable command. Keep code uncommitted for review.

Full10command review cleared after adding reuse attempt checksum validation:
attempt.request_idmust match digest(oldrequest), in addition to exact requested
messages/settings/model and received state. Offline full10check and a deliberately
tampered receipt negative control pass.9reused decode results match completed
3task artifacts. No model/network/native-reference calls in preparation/review.

## 2026-11-07 — mechanical recovery after full10 test-file hash interruption

The user-run output boundary_prompt_style10_20261107_113807 stopped after receiving
all3task16 responses because a test file was edited during execution. The source
freeze incorrectly included tests. Preserve the failed directory, its snapshot
and ledgers; do not overwrite hashes or restart its one-shot worker.

New-run source freezes exclude tests while retaining all production Python,
requests, data and imported response dependencies. Add --continue-from to import
both received checkpoints and inherited reused_calls into a fresh directory.
Require a stopped source, its worker lock, exact complete request identity,
received state/request checksum and inherited receipt/content hashes. Validate
the old freeze, allowing only this recovery controller and tests to differ;
other production/data/request drift blocks continuation. Unresolved attempts
block instead of being regenerated. Prompts, settings, parsing and scoring stay
unchanged. The source run has12available responses and18remaining slots.

Verification before delivering continuation:21offline tests PASS; actual-source
check-only gives30slots/12reused/18new,12decode-parity checks PASS, source directory
byte hashes unchanged, new-attempt count0, no model/native evaluation launched.
The shell remains foreground by default at the user's preference.

## 2026-11-07 — user promotes soft BVA as the boundary arm

User explicitly selects soft BVA as the main BVA pipeline and asks to place
deprecated implementations in a subfolder of the BVA module. `--arms boundary`
now runs direct soft-guided input generation. Keep the exact registered soft
system/common/guidance and single-PUT packet at input_budget20; spec/contract
remain normative, and code only encodes the JSON values supplied by the model.
There is one completion per allocated PUT, with no template eligibility,
selection call, abstention gate, target compiler or worksheet stage.

Main BoundarySettings contains only input/base-example/token/context/temperature/
seed settings. The adapter splits the existing task input budget equally over
visible base-passing PUTs in existing visibility order. It allocates no more PUTs
than input slots, records budget-exhausted PUTs explicitly, deduplicates and never
redistributes unused shares. Multi-PUT allocation is an engineering extension;
the10task diagnostic evaluated one PUT per task, not this multi-PUT setting.

Typed-selection/context/compiler/literal and checked-grounding implementations
move to boundary_value_analysis/legacy/ with explicit legacy imports in their
audits/tests. Legacy is not a default/fallback. Restore method invocation in the
currently empty composition adapter so the selected method is actually executed.
The shared encoder, domain/reference validation, generation freeze, native repeats,
cohort/data keys and CLI method name remain in use. New soft checkpoints/call keys
are disjoint from legacy checkpoints. Preserve historical outputs/manifests;
strict historical replay still requires its original source/environment. Frozen
input rescore restores the original method's accounting from saved protocol
configuration, so old selection/compiler inputs are not relabeled as soft.

Validation:342modular/development tests PASS, including new single-call soft
integration, strict decoding, budget/dedup, no-template gating removal, no legacy
runtime imports, source/settings mismatch and immutable read-only replay checks.
Offline replay of all10saved soft responses gives exact request/decode parity.
No new model/benchmark/native-cohort experiment launched. Unit integration tests
use synthetic fixtures. Results7soft/6direct on outcome-selected10tasks remain
descriptive; promotion is a user decision, not a general efficacy conclusion.

## 2026-11-07 — user-authorized soft precision-tool diagnostic, Phase A

User says to continue the precision-tool plan, then requests a trace explaining
which weakness remains and why naive/direct sometimes succeeds. Implement and
evaluate Phase A before changing the active soft default. No model calls.
Prior art/limits: archived BVA v5 constructed targets but lost selection/context;
v47menu selection was no-go. This diagnostic measures construction from existing
seeds, not whether an LLM selects concepts well.

Frozen source:boundary_prompt_style10_20261107_120909, exact10known-bugPUT cohort.
Read saved soft/direct decoded inputs and validate saved response/request identity;
do not consult reference/native outcomes during candidate generation or selection.
Task/PUT ids do not choose transformations. Extract complete named seed values by
literal parsing/binding to the task signature; use original decoded input order.

Supported anchors are top-level parameters whose seed value is a finite Python
float, plus string parameters with a syntactically direct float(parameter) call
in the supplied PUT or public contract. Recognition is a location cue, not a
semantic/domain guarantee; unsupported syntax remains unsupported. No integer
widening, nested-container mutation, character-code tool or relational solver.
For each eligible seed/parameter, preserve other arguments and construct the
finite math.nextafter neighbor below and above, round-tripping numeric strings
with repr(). Record adjacent float bits and unchanged non-target arguments.
Do not construct inf/NaN. Base/domain filtering remains post-freeze reference work.

Anchor order:seed index ascending, then declared parameter order. Enumerate all
below candidates in that order, then all above candidates (one per anchor per
round). Deduplicate against all original seeds and earlier generated candidates
using exact encoded args/kwargs. Construction receipts are checked independently
of task outcomes. This order is fixed before additional native evaluation.

Primary fixed20policy:retain the first10distinct original soft seeds, append up
to10distinct expansions from the above order, then fill any remaining slots from
the remaining original seeds. No rejection-driven replacement after domain/base
filtering and no score-based selection. Compare with original soft/direct batches
under budget20. Separately evaluate the full original-soft-plus-expansion pool as
a construction ceiling, explicitly outside the primary20input budget. All fixed
and pool inputs for all10tasks freeze before any new reference/native evaluation.

Use standard corrected reference/domain checks, two native repeats, shared input
cache and immutable read-only replay. New output directory; source artifacts and
prior report hashes are frozen and must remain unchanged. Report rejected domain,
base duplicates, wrong value vs timeout, seed retention and whether an exposing
candidate was absent, unselected, rejected or executed without exposing the PUT.

Phase A gate:fixed20must add at least one stable value-mismatch PUT relative to
original soft and retain every soft-detected PUT (including its resource case).
Unlimited-pool gains alone do not pass. No post-outcome budget/order/transform
tuning to rescue a failed gate. Phase B remains conditional; its writer/interface
and controls need a prospective amendment before model calls. These10outcome-
selected tasks are post-hoc mechanism checks, not general efficacy evidence.

## 2026-11-07 — conditional Phase B, before any new model generation

Phase A completed at boundary_precision_phase_a_20261107_152738:fixed20tool8PUTs,
soft7,direct6; new stable value-mismatch99and no soft losses. Pool ceiling8also.
The predeclared gate passed. Continue the user's authorized plan to test direction
selection with one new writer response per each of the same10tasks. This is a
known-case mechanism diagnostic, not an expanded/held-out efficacy trial.

Use the same source PUT/spec/contract/base packet,Qwen27,sampling seed314159+task,
temperature.7,completion2048/context8192,input20. Adapt the soft output envelope
to inputs plus expansions. Request at most2optional directives containing only
seed_index,parameter,quantity(float/parsed_float),anchor,neighbors(adjacent).
An anchor must equal the referenced seed's finite scalar value (after float()
for a supported numeric string). No new anchor injection, nested contexts,
unbounded tools or mandatory selector. Unsupported directives do not discard
otherwise valid seeds. Truncated/malformed seed JSON follows the strict policy;
no semantic retry, repair, model fallback or outcome feedback to the writer.

Generate the same float candidate pool as Phase A from each new seed batch.
Concept order follows the request list, then below/above; use only candidates
whose receipt matches a valid directive. A directive can provide at most2new
neighbors; total distinct selected expansionsK<=4. Generic control takes the
firstKdistinct candidates from that identical writer's pool. Both retain the
same first10seeds and fill the remaining budget20with remaining seeds in order.
Matching actual K prevents a concept benefit from merely keeping more seeds.
When K=0both controls are the full new seed batch. Record unsupported/empty
directives explicitly; generic controls are conditioned on K, not independent
autonomous tool policies. Also report the new20seed-only batch and original saved
soft batch. Existing direct/Phase A evidence remains separate, not regenerated.

Preflight metadata and tokenize all10requests before completion dispatch. Use
recorded bounded transport and one-shot worker. Freeze all new seed/directive
responses and all four input-policy batches before any corrected reference/PUT
evaluation; use the standard corrected reference/domain stage,2native repeats,
execution cache and immutable replay. Disclose shared writer cost once, separate
from historical soft costs. Invalid/incomplete requests are outcomes, not replaced.

Phase B gate requires at least one task with a new stable value mismatch for
concept-directed expansion over the matched generic control, no generic-detected
task loss, and retention of all original soft-detected tasks. New seeds vs old
soft is not a causal concept comparison because output instructions differ.
If concept and generic tie, or only the changed seed writer improves, report no
demonstrated concept-selection gain and keep the active default unchanged.
Never retune schemas, quota, ordering or thresholds after seeing these outputs.

## 2026-11-07 — post-hoc interface-loss audit, not a Phase B rerun

Phase B completed10received responses/0unknown/0truncation,16206known tokens.
Primary seed/concept/generic policies each detect4PUTs vs original soft7; the
gate failed. Five responses (2/76/99/124/140) have a single outer Markdown JSON
fence and were rejected as invalid_writer_envelope by the frozen strict parser.
Other request errors include boolean/list neighbors instead of the required
adjacent string and a wrong seed-index/anchor binding. Only one directive was
admitted, on72, so the primary result provides little coverage of direction
selection. It must not be presented as evidence that concept selection intrinsically
finds only4bugs or that the tool cannot construct appropriate values.

User asks for the exact loss mechanism. Perform a separate read-only response
audit: strip only a complete single outer ```json...``` fence, then pass the
unchanged interior to the same writer/seed/directive validators. Do not repair
any values, requests, neighbors mode, quantity or indices. Freeze the derived
batches for all10tasks before scoring with standard reference/domain and2PUT
repeats. Reuse completed writer responses;0newmodel calls. Label the new output
post-hoc envelope-normalization audit; do not overwrite original responses,
primary snapshots/metrics or gate. Compare recovered seeds, matched concept/
generic, and an explicitly separate autonomous Phase A generic fixed20policy
on the same recovered seeds. The latter diagnoses available construction
capability; its Kdiffers and cannot establish concept-selection value. No new
prompt run, retuning or default promotion follows from this audit.

## 2026-11-07 — user requests full HumanEval soft BVA run

Run the active boundary arm over all164HumanEval tasks using the existing frozen
qwen35_27b_humaneval164cohort, not new PUT generation. Cohort SHA256 identity:
2a32bae531c339f2e403d748984ce5775734bdd8fd0fc9a02620392fbc23c7ed.
It contains1634generated PUTs and1465base passes. Preserve existing eligibility:
32/136skip generation_shortfall;65/127/132/145/163skip no_base_pass. Expected
eligible157tasks/1454base-passing PUTs, at most1454logical generation calls.
No prior V11-specific resource exclusions are silently applied to this new run.

Use current BoundaryArm/soft-bva-v1, target_programs10,input_budget20per task,
equal fixed shares in existing visibility order, no redistribution. This implies
typically2–3inputs per PUT, unlike the known10diagnostic's20inputs for one PUT.
An optional budget preference was requested while preparing; absent a user
override, run the existing pipeline configuration. No precision expansion,
concept requests, legacy selection/compiler or plain regeneration is enabled.
Qwen served modelqwen3.5-27b-awq,context8192,completion2048,temp.7,seed314159+task.
Use the current strict JSON parser; no fence recovery, schema/semantic retries
or post-outcome tuning. Existing bounded transport retries are recorded separately.

Before launch, inspect all164task signatures/cohort eligibility and prepare exact
request identity hashes for every allocated PUT. Require exact endpoint model/
context and tokenizer readiness. Freeze production code/data/cohort/settings/plan
and verify before model tokenization/completions and each task stage. A guarded
recorded client only dispatches registered request identities. New output folder,
exclusive one-shot worker and detached controller; no automatic restart/reset.
Source snapshot copies allow inspecting the frozen source while the job runs.
Keepalive every20min is recorded separately. Endpoint/keys stay in private config
outside the repo; never archive environment files or log credentials.

All164task input batches freeze before corrected HumanEval+reference/domain and
PUT evaluation. Use3sper-input timeout,two native repeats and existing execution
cache. Controller writes progress/status, checks read-only replay on completion,
then writes a result digest and report. Preserve sealed plain baselines and all
previous diagnostic checkpoints; no reuse/regeneration of an unmatched baseline.
This full run reports current BVA behavior and costs. There is no call-matched
plain control or held-out efficacy claim. Explicit skips,context-limit failures,
generation rejections and resource outcomes remain in the denominator breakdown.

Prelaunch engineering checks:368modular/development tests PASS, including exact
full-cohort eligibility/request planning, dispatch guard rejection, source/archive
drift and stopping keepalive before final summary accounting. Offline preparation
on the actual cohort confirms164requested/157eligible/1454planned calls. Exact
Qwen27/context8192metadata and tokenizer probe13PASS,0experiment completions at
this point. Archive the preregistration; later unrelated note edits are not live
execution dependencies. Tests and unrelated audit scripts are excluded from
runtime guards; executed production modules/data/request plan remain frozen.

## 2026-11-07 — continuation after live scoring/runtime edits

User requests status check. The full run stopped on a source guard at493received
responses and52complete input batches, before all-input freeze or any evaluation.
Live put_evaluation.py changed from full2repeat policy to confirmation of only
first failures;worker.py also acquired a comment after the stop. Do not overwrite
those live-worktree changes or silently mix the new scoring policy into the run.

Continue the original user-authorized full run in a fresh output using a read-only
copy of its intact source archive. Pin imports with Python -P and an isolated
PYTHONPATH;native sandboxes copy worker/contracts from that same frozen runtime.
Only inert package namespace initializers absent from the original archive are
bootstrapped;no generator,parser,scoring or data logic changes. Keep original
Python/dependency versions. Full164cohort,model/settings/request identities and
20input/task allocation remain identical. Share the existing execution cache.

Import all493received request/response/attempt checkpoints after exact request
hash/received-state checks, including unsuccessful generation outputs; preserve
the2archived unknown transport attempts. Copy the52completed input/packet batches
unchanged, recording source/content hashes. Partial-task calls replay through
the recorded client;do not reset any attempt counters. At most961newlogical calls
remain out of the original1454cap. Imported usage is historical and disclosed
separately. Preserve old stopped output byte-for-byte;new worker has its own
one-shot marker and no automatic restart. Live-worktree source edits no longer
affect the isolated execution;the frozen runtime/data/imported artifacts remain
guarded. Existing keepalive,global input freeze,full2native repeats and terminal
read-only replay/report are unchanged.

Recovery checks before launch:4checkpoint-preservation/mismatch/unknown/archive
tests pass. Actual offline import confirms493responses/52batches/961remaining and
original artifact hashes unchanged. Import probe resolves both scorer and worker
to the frozen runtime. A synthetic native smoke (0modelcalls) executes both full
repeats for failing and passing inputs and matches immutable replay.
This is mechanical continuation,not a new method,scoring amendment or rerun of
received requests. Do not classify this as endpoint failure;endpoint checks200.

## 2026-11-07 — user-authorized conditional PUT confirmation

User explicitly accepts: first PUT pass stops; first fail/error/timeout receives
one confirmation run, counted as detection only if that also fails/errors/times
out. Implement this evaluator optimization without generating or scoring a new
benchmark. Every input keeps repeat0; only first-run failures use repeat1with the
same seed, timeout, expected output and tolerance. Shared cache identities remain
separate per repeat. Reference/domain validation still repeats all inputs twice.

Record original input indices in each program's outcomes.retested. The unstable
field now covers only those retested inputs, so it no longer measures first-pass
inputs that might have failed on a second run. Stage configuration identifies
confirm-first-failures-v1/retested-inputs. Confirmation artifacts use a distinct
_retry_1.json path to avoid interpreting old full-suite second-run checkpoints
as a subset. Existing frozen runs/results remain historical and are not migrated
or automatically resumed. Validate subset indexing, transient failures, all-pass
and empty batches, cache/no-cache operation and immutable replay with engineering
fixtures and local sandbox checks; no model calls or new benchmark run.

Default per-input cache execution isolates each call. Without that cache, the
confirmation job contains only the failing subset, so it omits state changes
from first-pass successes. Stateful batch execution therefore has a different
history from the historical full-suite second run;do not claim replay equivalence
across these protocols. Both are recorded through stage configuration/checkpoints.

## 2026-11-07 — evaluation-only continuation after sandbox spawn failure

Full generation is complete:1454received responses and164globally frozen input
batches in boundary_soft_humaneval164_resume_20261107_195417. The worker stopped
after33task results at task33PUT evaluation, with FileNotFoundError naming bwrap
at subprocess spawn,not a PUT outcome. The binary is currently present in the
standard system path and a fresh frozen-runtime sandbox smoke passes. Exact
transient cause is unestablished;do not label the failure as a detected bug.

Continue only evaluation in a fresh output using FrozenInputsGenerator and the
same isolated original generator/scorer/native-worker runtime. No model backend,
endpoint dependency,generation request or keepalive is needed. Validate all164
input hashes against the completed freeze,restore original visibility packets,
and copy completed reference/native checkpoints with content receipts. Reuse
the same per-input execution cache. Preserve both earlier stopped outputs.
Original full2repeat policy,3stimeout,seed,oracle,cohort and input budget stay fixed.

Pin parent PATH to os.defpath so the sandbox executable lookup and subprocess
PATH agree. Preflight its binary/hash and a real cold native smoke in the detached
worker. Do not change the frozen executor or fall back to unsandboxed execution.
If the same bwrap spawn FileNotFoundError recurs while the binary exists, allow
one recorded evaluation-only retry after a passing smoke;reuse all checkpoints/
cache entries. Other failures stop. No retry or regeneration of LLM responses.

Archive the evaluation controller itself and freeze source/input/checkpoint
dependencies. New one-shot worker and separate progress/status. Require identical
global input freeze and immutable read-only replay at completion. Report parent
generation costs separately from0newmodel calls and disclose imported execution
checkpoints. This repairs infrastructure/continuation only;no scoring optimization,
new testing method,post-outcome input change or default promotion is introduced.

## 2026-11-07 — compare full soft BVA with the stored naive baseline

User explicitly points out cached naiveLLM data and requests its use. Reuse only
the unchanged admitted plain batches in v11_concept_inputs. Its164task ledger,
cohort SHA,task/spec/domain metadata and sampling settings match the completed
BVA run. Original naive156writer responses,2481admitted calls,31empty generated
batches and8source task skips are preserved. Do not reparse/repair raw responses,
generate missing calls or synthesize new inputs. Missing source plain batch means
an empty input set,with its original source skip recorded.

Export a plain-only frozen input view in a new directory with receipts tying each
record to its original whole-batch freeze. Evaluate on BVA's exact full cohort
(157eligible tasks/1454base-pass PUTs) under the same corrected HumanEval+reference,
original full2repeat scorer,3stimeout,seed and execution cache/frozen runtime.
No model calls. Old naive verdict72must not be subtracted directly from BVA61,
because the old evaluation/reference protocol differs. Preserve the old source
and the sealed44task baseline entirely unchanged.

Original naive input generation/evaluation excluded17resource-risk PUTs;its cohort
checksum itself was unchanged. Validate those source-bound exclusions and report
both full1454target results and the1437common historical target intersection.
No current BVA or naive input is discarded based on detections. BVA's completed
native verdicts remain fixed;rescore naive only. Report shared/BVA-only/naive-only
PUTs and per-task lists,wrong-value versus resource/exception detections,and valid
input yield. Verify immutable replay and unchanged source hashes at completion.

This is a retrospective same-target/oracle comparison of two stored generators,
not a prompt-only or call-matched experiment. Both use a nominal20inputs/task,
but BVA made1454per-PUT writer calls,naive156task calls;visibility/output schemas
and generation epochs differ. Disclose costs and original empty/skip batches;
do not interpret a raw winner count as an isolated effect of BVA knowledge.

Secondary descriptive normalization is fixed before inspecting the new naive
verdicts:for each task,k=min(valid_BVA,valid_naive). Average each PUT's detection
over uniform k-subsets of that method's valid inputs using1-C(n-f,k)/C(n,k),where
fcounts its recorded confirmed failing inputs. No new execution or selected
prefixes;zero-k tasks contribute0. This analytical conditional mean is not the
primary result,a new trial or a statistical superiority claim. Primary remains
observed shared/BVA-only/naive-only on full1454and historical common1437targets.

## 2026-11-08 — packaging diagnostic and matched batch Direct/Soft BVA

User explicitly authorizes both steps and requests LLM calls after40minutes.
Request timestamp2026-11-07T18:37:40Z;not-before2026-11-07T19:17:40Z
(2026-11-08 02:17:40Asia/Ho_Chi_Minh). No endpoint/tokenizer/completion/keepalive
before the deadline. Prepare/review/tests and CPU-only repair audit may run now.
This follows the prior prompt-style diagnostic(first10soft7/direct6) and full
retrospective comparison(BVA61/naive44). All30BVA-onlyhave0naive novel inputs;
this diagnostic tests packaging losses,not an untouched held-out efficacy claim.

Step1: authenticate every original raw plain response against the pre-existing
export source snapshot,plus all admitted batches against their original freeze.
Apply fixed rules to all164tasks,not a list selected by detections. Only parse
complete JSON responses using the existing parse_json fence handling;do not
recover truncated/invalid JSON,execute expressions,change values or generate new
records. Keep at most the original20raw slots. A repaired view has one encoding
per raw slot. Existing viable admitted bindings are retained byte-for-byte;
unchanged source and receipts preserve every original admitted/raw record.

Wrap a single literal as the sole required positional argument only if static
annotation or unconditional contract type/iteration proves it compatible and
the old binding is absent or incompatible. Literal-only decoding;empty kwargs;
no defaults,keyword-only,multiple parameters or unproven type repairs. Bare list
args can be ambiguous;preserve a compatible existing binding. Infer iterable
requirement only from unconditional contract iteration/first generator in a
top-level assert all;ignore short circuits/conditionals/rebinding. No oracle or
PUT result is used to select/authorize repairs. Unsupported cases stay rejected.
Record raw index,old/new literals,old admitted record and static proof. Preserve
the original baseline and sealed44run. New repaired export/freeze/receipts and
evaluation live in a fresh directory. Same1454targets,original frozen full2repeat
scorer/reference/3stimeout/cache as the completed61/44comparison. Compare repaired
naive to original44 and BVA61 with exact task-local identities,including old30.
This is a packaging sensitivity diagnostic,not a fresh matched generator trial.

Step2: two new arms direct and soft_bva,one batch completion per eligible task
per arm(max314logical calls). Same frozen cohort157eligible/1454base-passPUTs,
same common spec/contract/base/code packet,named-arguments-v1schema,CallBuilder,
shared InputGenerationMethod parser,20inputs/task,2048output tokens,8192context,
temperature0.7,seed314159+task. Direct appends empty guidance;Soft appends the
existing GUIDANCE verbatim. No other arm-specific prompt/schema/mechanics changes.
All generated inputs run against every base-pass PUT of their task,including
PUTs removed from writer visibility for context size. Pre-tokenize BOTH prompts,
select one common visible list fitting the larger prompt+completion+128reserve,
and freeze the complete request/visibility plan before any completion. If neither
can fit one PUT,record empty inputs for both but retain targets in evaluation.
Task eligibility skips remain unchanged. Arm order alternates by task parity.
No generation retry after received invalid/schema/truncated responses;existing
bounded transport retries(max3) are retained and unknown attempts disclosed.

Freeze every batch before reference/native execution. Both fresh arms use the
same current confirm-first-failures-v1scorer,corrected reference repeated twice,
seed271828+task,3stimeout and cache. This differs from the original full2repeat
runtime retained for Step1;do not interpret fresh versus historical totals as a
prompt-only effect. Primary comparisons are WITHIN the fresh paired run,using
all eligible tasks,including empty/invalid generations. Report exact shared/
direct-only/soft-only PUTs,per-task paired counts,stable wrong values separately
from exceptions/timeouts,input validity/coverage,actual writer tokens/calls and
transport/keepalive costs. No post-outcome prompt tuning or task selection.

Independent read-only reviewer before outcomes:batch_fairness_review. Must-fixes
incorporated before launch:conservative ambiguity proof,one raw slot/record,
corrected receipt hashes/unchanged flags,shared context trimming,parity order,
review/test+deadline gates,isolated readonly runtime,observer cost accounting and
native serialization. Repair and fresh native scorers acquire the same flock;
remote Step2 generation may start at deadline during Step1CPUscoring,then waits
for the lock. No KeepAlive before deadline. Endpoint metadata-only polls after
deadline for up to6h if expected Qwen27/context8192not available;no substitution.
Detached one-shot worker,never reset markers/unknown ledgers. Replay and frozen
source/data/input checks required. User did not request commit/default promotion.

Prelaunch review receipt2026-11-07T18:54Z:independent batch_fairness_review PASS,
including packaging-specific(not unchanged-input) reporting and waitable metadata
states ExpectedModelMissing/ContextTooSmall.422tests passed before CPU launch;
31targeted offline tests passed after final reporting/scheduler changes. Repair
evaluation is detached;fresh batch worker has not called model and is scheduled
only after this final review. Source/test hashes recorded in readiness receipt.

## 2026-11-08 — resume matched batch after endpoint tokenizer404

User supplies the endpoint again and explicitly requests continuation. Stopped
source bva_batch_matched164_20261108_021740 has226received responses/113perarm,
314frozen requests and88missing logical responses. One archived unknown attempt
for115/soft_bva remains attempt1under the original max3transport policy. No global
input freeze or native scoring was reached. Private local configuration pointed
to a different endpoint;updated outside repo to the supplied endpoint,expected
Qwen27/context8192and tokenizer13verified,0newcompletions before recovery review.

Continue into a fresh output,never reset old one-shot markers or old attempt
ledgers. Validate old runtime/request_plan/visibility hashes and every received
request/attempt identity. Capture current response byte hashes as recovery
receipts;do not claim an earlier response freeze that did not exist. Copy all
received calls,unknown history,complete batches and keepalive receipts. Re-decode
saved batches using cached calls only before model initialization. Leave the
original source directory byte-for-byte unchanged and require final hash match.

Restore the exact frozen runtime/data/cohort,adding only an isolated recovery
controller. Reuse original generate/evaluate/paired_verdicts and the saved request
plan;do not call prepare_packets or reselect visibility. Imported received calls
are read from cache,including a received arm of a partial task. Only88missing
logical responses remain eligible for new inference. Preserve request-level
attempt counts/max3,unknown transport histories,sampling,20input/task budget,
named argument schema/parser,arm order,reference,3stimeout and original paired
confirm-first-failures scorer. Generation epochs differ after service recovery;
disclose without replacing inputs or tuning prompts.

Keepalive receipts and writer tokens include imports exactly once;report new
continuation usage separately. Mutable unreceived current checkpoint files are
not frozen before transport recovery;their original versions remain in source
and receipts. Archived unknowns and received responses stay immutable. Freeze all
task inputs before native scoring,serialize native phase with the original lock,
require source/input hashes and immutable replay. Worker one-shot and detached;
metadata-only wait for expected endpoint if unavailable. Independent recovery
review and tests must pass before completion calls. No new method/benchmark,
generation quota change,automatic semantic repair or default promotion.

## 2026-11-08 — user-operated local preset console

User requests persistent run/config history and interactive settings,with future
experiments launched by the user from presets. Use existing self-hosted Prefect
3.9.2rather than a new UI/server. Prefect dependencies live in a separate venv;
benchmark subprocesses retain final/.venv. Current approved batch28517continues
in its previously frozen runtime and is not adopted/restarted by the console.

Register full resolved parameters for each deployment:full paired batch,
known10paired batch,3task smoke,and historical per-PUT shared20allocation.
Parameters explicitly include seeds/token/context/input budgets,tasksubset,
arms,model and scorer. Input unit is per TASK per ARM;per-PUT mode divides it.
No LLM/native calls from preset creation,history import or preview_only=True.
User pressing Run with preview_only=False authorizes the selected bounded run;
agents prepare/review presets and do not auto-launch new model experiments.

Each real run freezes its resolved config,cohort/code/data and sampling into a
new directory before generation. Endpoint/APIkey stay in private600profiles
outside repo and outside Prefect parameters. Batch arms share a single packet,
parser/builder and tokenization fit,alternate arm order;only guidance differs.
Existing reference/scorer/cache/method implementations are reused. Full2repeat
and conditional confirmation are explicit separate scorer choices. Native jobs
share the existing flock;one console flow at a time and external-writer checks.
Stop/resume preserves calls,unknown history and attempt caps in a new output;
never reset marker/ledger. Path-only reference/identity metadata may be rebuilt
with original bytes preserved in receipts. All actual runs require input freeze,
source hashes and immutable replay. Completed reporting separates error/timeout
from stable returned-value mismatch through the existing paired analyzer.

Historical outputs indexed read-only as imported records/artifacts;no hidden
replay,generation or inference. Self-hosted localSQLite/UI127.0.0.1:4200only.
Independent reviewer prefect_console_review PASS after fixes to private-profile
uniqueness,full preset defaults,observer join,cancelled/stale resume,and service
port identity.444benchmark/development/unit tests PASS before listener enable.
Browser/API smoke uses preview_only=True and must produce0model/nativecalls.

## 2026-11-08 — infrastructure amendment: resume matched batch evaluation

User explicitly authorizes fixing the stopped Direct/Soft batch and continuing.
Source:bva_batch_matched164_resume_20261108_104541;314receivedresponses covering
157eligible tasks/two arms,164frozen input batches,60finished evaluation tasks.
Task60PUT7 uses reduce(operator.add,range(1,n+1),0),with n2147483647 in Direct.
A pending Python SIGALRM cannot interrupt that C call;outer wall guard aborted
the whole evaluator. This is an execution recovery,not a new generation trial.

Before resuming,add a worker marker around actual oracle/PUT calls. Only a
single-input oracle/evaluate job whose marker is active at the outer wall
deadline may return timeout(sandbox_wall_guard). Startup/import without active
user call,invalid marker and multi-input jobs still raise infrastructure error.
Keep timeout3s,existing outer10+timeout wall allowance,reference/comparator,
confirm-first-failures policy,both arm inputs/visibility/settings/seeds unchanged.
No fresh model/tokenizer calls. Runtime patch changes only execution.py/worker.py
in a new copy of the frozen runtime;old source/output remain immutable.

Reuse completed native checkpoint bytes,record every copy;rebuild only path-based
reference provenance in the new runtime. Existing execution-cache identity
includes both patched files,so new executions cannot accidentally hit old-runtime
cache entries. New run uses original shared native lock. Native NumPy pass/fail
smoke,regression for blocked C call versus startup hang,ledger/source hash checks
and immutable replay required. Do not use partial counts as final comparison.
Final Vietnamese report includes shared/direct-only/soft-only PUTs,valid inputs,
task totals,wrong-value witnesses separately from timeout/error,total received
responses/known tokens/unknown historical attempt,and0newmodelcalls.
Publish one Prefect record for the new output;old stopped rows stay suppressed.

## 2026-11-08 — amendment: catalogue testing arms EP/BVA/DT

Người dùng yêu cầu implement `final/PLAN_TESTING_ARMS.md` và tăng token budget
vì có thêm instruction/catalogue. Amendment này đăng ký code/config cho run
**chưa thực hiện**; phiên implement chỉ chuẩn bị code, preset và engineering
fixtures/review, không launch/schedule/resume experiment, evaluation hay inference.
Kết quả lịch sử V7/V11 classical mixed và soft-BVA diagnostic không được dùng để
claim hiệu quả của các arm mới. Không tái hiện hoặc mô phỏng paper.

Arms: `ep_bva` là cấu hình chính (weak EP rồi normal BVA trên class edges),
`equivalence` và `bva_normal` là ablation; `decision_table` là arm DT riêng.
`ep_strong`, `bva_robust`, `bva_worst_case`, `ep_dt_bva` là opt-in variants, không
bật đồng thời tất cả trong preset mặc định. Pipeline default vẫn `plain`;
`boundary` là soft BVA per-PUT với `BoundarySettings` giữ nguyên. Batch comparator
có thể dùng `plain`/`direct`/`soft_bva`; per-PUT `boundary` có allocation/call count
khác nên không ngầm xem là matched-call comparison.

Mỗi eligible task/arm có tối đa một generation completion sinh compact catalogue
và inputs cùng lúc; không feedback loop. Shared spec/domain/base tests/visible
PUTs, order policy, model/sampling/seeds, context cap, CallBuilder, input freeze,
corrected reference, timeout, execution cache và scorer được dùng chung trong
comparison. Guidance kỹ thuật cố định, không quá 8 dòng/arm; shared prompt và
catalogue schema là phần riêng. Expected outputs chỉ do corrected reference
cung cấp sau global input freeze. Không dùng catalogue để cung cấp oracle output.

Preset definitions mới:

| Preset/arm pair | Cohort/task selection | Budget tối đa |
|---|---|---|
| Plain vs `ep_bva` chính | `boundary_smoke`, 6 task, 1 representative PUT/task | 12 logical calls, 240 input records |
| Plain vs `equivalence` | `equivalence_smoke`, 6 task, 1 representative PUT/task | 12 logical calls, 240 input records |
| Plain vs `bva_normal` | `boundary_smoke`, 6 task, 1 representative PUT/task | 12 logical calls, 240 input records |
| Plain vs `decision_table` | `equivalence_smoke`, tasks 11/85, 1 representative PUT/task | 4 logical calls, 80 input records |

DT eligibility chọn theo spec có hai conditions tương tác: HumanEval/11 XOR hai
bit; HumanEval/85 element chẵn và vị trí index lẻ. Không chọn theo hidden outcomes.
Chưa tạo một development group DT mới. Không tự nối smoke → dev → check/full;
mỗi run tiếp theo cần quyết định riêng của người dùng.

Mọi arm trong comparison mới dùng 20 inputs/task/arm, completion cap **4096
tokens/call**, context cap 8192 tokens, temperature 0.7, input seed 314159 cộng
task number, reference seed 271828 cộng task number, timeout 3 giây/input và
scorer `confirm_first_failures` trừ khi người dùng đổi config trước Run. Smoke6
có completion upper bound 49,152 tokens; smoke2 là 16,384 tokens. Caps không phải
usage thực tế. Bốn preset cũ ghi rõ 2048 completion tokens/call để giữ budget;
submitted config/code snapshots không bị thay đổi. CLI mặc định 4096 khi có arm
catalogue, 2048 cho plain/soft BVA cũ; explicit override được lưu trong settings.
Console form/config mới default 4096. Tokenization chọn cùng visibility đủ chỗ
cho tất cả arm sau completion reserve; context overflow được ghi rõ, không đổi
riêng visibility của một arm.

Pydantic kiểm schema, tagged argument data và duplicate/structural errors;
CallBuilder vẫn encode named values. `math.nextafter`, interval checks và
`itertools` xử lý phần mechanical có metadata. Không execute Python predicate
hoặc code do model viết trong catalogue. Catalogue thiếu/sai ghi
`catalogue_invalid`, giữ input hợp lệ để shared domain/reference đánh giá.
`catalogue=false` trên console hoặc `--catalogue-off` trên CLI là instruction-only
ablation để đo chi phí catalogue; giữ completion cap chung và không claim đã
kiểm technique coverage.

Measurement chạy sau freeze/domain/reference, trước PUT evaluation. Coverage
hiện chỉ đo **novel reference-valid inputs**; rejected/base-duplicate inputs
không được credit. `covers` là self-report; thiếu covers có thể đo mechanical
subset nhưng phần chưa suy ra được là `pending`. Một input phủ nhiều obligation
vẫn chỉ là một input. Base-call coverage hiện `pending`, không diễn giải missing
novel coverage thành bằng chứng rằng base tests chưa phủ obligation đó.

Mechanical BVA chỉ đo khi parameter/selector, numeric endpoints, context và
nominal đủ máy đọc. Normal design size đếm supplied coordinate obligations,
không chứng minh catalogue liệt kê đủ dimensions của spec. Float neighbor dùng
step theo spec hoặc adjacent representable value; không dùng epsilon cố định.
Single-fault phải giữ các declared dimensions khác ở nominal, kể cả khi nhiều
dimensions dùng cùng một parameter. Unknown/prose dimensions và semantic grounding
vẫn `pending`. Strong EP mỗi surviving input chỉ credit một class combination;
contradictory labels không được Cartesian-expand thành nhiều combinations.
Worst-case/strong EP có cap; `budget_limited` chỉ tính khi declared design hoặc
Cartesian size biết được và vượt input budget. Thiếu dữ liệu để tính thì pending;
coverage thấp tự nó không chứng minh budget gây thiếu.

DT structural checks giữ ordered actions, source mapping `merged_from`, phân
biệt feasible/infeasible/unresolved và yêu cầu lý do cho infeasible combination.
Coverage denominator là **feasible original rules**; merged ID không tự credit
mọi original combination. ID mơ hồ giữa merged/original rules không được dùng để
phóng đại coverage. Thiếu original combinations hoặc proof feasibility thì giữ
pending. Các checks chỉ phát hiện phần overlap/contradiction máy đọc được,
không chứng minh spec semantics hoặc đầy đủ của catalogue.

`bva_robust` chỉ gọi model khi task metadata có
`testing_arms.out_of_domain_behavior_defined=true` và `testing_arms.spec_evidence`
không rỗng; thiếu eligibility thì `not_applicable` trước model call. Eligibility
không mở rộng shared domain contract. Input ngoài contract vẫn bị reference/domain
stage loại. Spec không định nghĩa reject behavior không được xem là robust đã test.

Report tiếng Việt mở bằng detection và giới hạn kết luận; nêu config/budget,
task/PUT/input counts với đơn vị và mẫu số, actual calls/tokens theo arm, fail/skip,
`catalogue_invalid`, `not_applicable`, `unresolved`, `budget_limited` và pending.
Raw detection dùng toàn bộ novel valid inputs. Matched-valid-input-budget dùng
subset ngẫu nhiên có seed theo task/pair, không lấy prefix và giữ task có matched
budget bằng 0. Unique confirmed detected PUTs/eligible PUTs tách khỏi detected
tasks và input counts; wrong-value, exception và timeout/resource báo riêng.
Catalogue coverage không chứng minh detection, detection không chứng minh
catalogue đúng. `ep_bva` vs `equivalence` so instruction package tổng thể,
không cô lập riêng tác dụng BVA.

Engineering fixtures bao gồm tháng, hai dimension/single-fault, float/context
admission, NextDay dependent day limit, grade overlap tại 4, salary DT/merge và
no-inflation regressions. Independent read-only review và must-fix regressions
là gate trước outcome mới; không suy ra efficacy từ fixture. Source/package
manifest phải giữ cả reporting helper và Pydantic version để replay phát hiện
thay đổi dependency. Mọi actual run sau khi người dùng bấm Run phải có một
Prefect record/source run, snapshot trước generation, global freeze, source
checks và immutable replay; chưa evaluation xong thì không đánh dấu Completed.

## 2026-11-08 — authorized launch: Plain vs EP+BVA smoke6

User yêu cầu chạy bằng endpoint riêng tư vừa cung cấp. Chọn đúng preset chính
`Smoke6 · Plain vs EP + BVA · chính`, không bật ablation/DT hay nối dev/check/full.
Frozen boundary smoke cohort gồm HumanEval/0,5,18,81,99,120; một representative
PUT/task. Hai arms `plain`, `ep_bva`, catalogue bật cho arm mới; 20 inputs/task/arm,
một generation call/task/arm, tối đa12logical calls/240input records. Completion
cap4096 tokens/call chung hai arms, context8192, temperature0.7, input seed314159,
reference seed271828, timeout3giây/input, corrected HumanEval+ reference và
confirm_first_failures scorer. Giữ order policy theo task parity của console.
Completion upper bound49,152tokens không phải usage thực tế; physical transport
attempts và unknown usage báo riêng theo retry policy hiện có.

Independent reviews trước launch PASS;484engineering tests PASS,710catalogue
before/after parity cases và16prompt variants unchanged. Chưa đọc outcome mới
khi ghi amendment. Endpoint metadata xác nhận qwen3.5-27b-awq/context8192 và
tokenizer probe13tokens; không ghi endpoint/key vào tracked artifacts/Prefect.
Prefect deployment tạo một flow-run; worker snapshot source/config/cohort trước
generation, global freeze trước oracle/evaluation, kết thúc bằng source checks
và immutable replay. Chỉ Completed sau evaluation và report tiếng Việt. Report
raw và seeded matched-valid budget, novel valid input counts, detected PUTs/tasks,
wrong-value/exception/resource, catalogue errors/coverage và pending semantics.
Hết smoke này thì dừng, không tự nối thêm run.

## 2026-11-09 — user-authorized full EP+BVA và Decision Table

User yêu cầu full pipeline EP+BVA và full Decision Table sau smoke6. Chạy một
full batch có ba arms `plain`, `ep_bva`, `decision_table` để hai comparison chính
Plain vs EP+BVA và Plain vs DT dùng chung một baseline mới, cùng visible PUTs và
cùng reference/evaluation. Không nhân đôi Plain trong hai run riêng. Full164
frozen cohort có164task records,157eligible generation tasks và1454base-pass
PUTs;7tasks không base-pass được giữ trong skip accounting. Không chọn subset
theo hidden outcomes. FullDT áp dụng yêu cầu full của user: denominator chung là
all eligible base-pass task/PUTs, không mặc định mọi task đều DT-applicable.
Catalogue not_applicable/unresolved/invalid và semantic limits báo riêng.

Budget:20inputs/task/arm,1generation call/task/arm,tối đa471logicaltester calls,
3140input slots/arm(9420slots tổng);completion4096tokens/call,context8192tokens,
completion upper bound1,929,216tokens trước ancillary keepalive/transport retry.
Modelqwen3.5-27b-awq,temperature0.7,inputseed314159+tasknumber,referenceseed271828+
tasknumber,timeout3giây/input,correctedHumanEval+reference hai lần và PUT scorer
confirm_first_failures. Shared packet jointly tokenized cho cả3arms;trim cùng
visible PUT list theo worst prompt khi cần. Order:plain/ep_bva/DT ở task chẵn,
đảo lại ở task lẻ theo console hiện có. So sánh EP+BVA vs DT là descriptive
secondary;không claim isolated technique effect. Không reuse smoke responses vì
visibility cohort khác;full là generation mới được user cho phép.

Không retune guidance/schema/parser theo smoke outcomes. Giữ catalogue-invalid
inputs cho shared reference;unknown semantic check vẫn pending. Chỉ sửa một
measurement bug trước launch:uncovered_boundary_values trả null(pending) nếu có
boundary chưa có missing_values,thay vì sum bỏ qua null ra0. Không đổi input
selection,freeze,oracle,scorer hoặc expected outputs. Engineering regression kiểm
all-known/mixed/unknown missing-values và3arm shared-baseline replay. Smoke source,
inputs/checkpoints/results không đổi. Full results chưa được đọc khi ghi amendment.
Independent prelaunch reviewer kiểm budgets/3armgenericwiring và applicability.

Hiện có run Direct/SoftBVA khác active trên cùng listener/GPU. Không cancel,
restart hay reload listener khi run đó hoạt động. Submit một managed flow mới
qua deployment đang served với explicit full parameters;Prefect serve limit1
xếp hàng phía sau. Config params được giữ ngay khi submit,source/cohort snapshot
riêng được tạo trước generation lúc worker nhận run. Không launch thêm bản sao.
Mọi physical attempts/unknown và keepalive1-token calls mỗi20phút được báo riêng;
471 là tester logical cap,không phải tổng mọi ancillary calls. Credential/endpoint
nằm trong private profile,snapshot riêng khi start;không đưa URL/key vàoPrefect.

Run hoàn tất generation global freeze rồi mới domain/reference và1454PUTeval,
source hash verification/immutable replay/report tiếng Việt trướcCompleted.
Chỉ hai comparison được yêu cầu trong chung run này;không tự nối thêm ablation,
rerun hoặc benchmark khác. Lưu và dùng lại đúngflow_run_id cho config/progress/
results/report;mỗi source run mộtrecord. Các kết quả chưa có giữpending.

## 2026-11-09 — two-endpoint routing correction before full generation

User xác nhận có hai endpoints và yêu cầu run ngắn hơn dùng endpoint mới;không
cần option chọn endpoint. Direct/SoftBVA full(314logicalcalls,2048completion)
được đổi private routing sang server mới;in-flight stream hoàn thành trên server
đã mở,next requests dùng route mới. Full3arms(471calls,4096completion) pin profile
riêng ở server trước đó. Cả hai readiness cùng modelqwen3.5-27b-awq/context8192;
không ghi endpoint URL/key vàoPrefect hoặc tracked artifacts. Không đổi config,
seeds,callbudget,prompts,input selection/scorer của bất kỳrun nào.

Giữ flow33a3c2fd-a517-4b82-afe7-43a2c3767f7c và dispatch bằng process riêng
thay vì chờ listener limit1. Atomic Scheduled→Pending default transition với
force=False phải ACCEPT trước khi engine dùng sameflowID;fcntl chống2dispatcher,
output không tồn tại,run chưastart,không tạorecord/callbudgetthứhai. Generation
wait chỉ chặn writers cùngendpoint;unknown routing vẫn chặn. Nativeevaluation
vẫnsharedlock.4offline dispatch/routing regressionPASS,independentclaimreview
mustfixđãápdụng. Không thêm optionchọnendpointUI. Source snapshot riêng tạo trước
firstgeneration;existingrun source/checkpoints không sửa,private routing là
external transport config được user cho phép đổi.

## 2026-11-09 — user-requested native timeout8seconds continuation

User yêu cầu nâng timeout_sec từ3 lên8giây/input. Áp dụng cho cảhai full runs và
newconfigdefaults/presets. Tại amendment cảhai còn generation,chưa có bất kỳ
oracle/evaluation checkpoint nào. Dừng originalworkers rõlýdo useramendment,
giữ source/config/inputs/calls/checkpoints cũ nguyên. Tiếp tục qua NEWoutput,
flowrecordmới/sourcecontinuation link,normalize config timeout8;clone đúngfrozen
runtime/source của từng run,không đổi prompt,model,seeds,sampling,completioncap,
inputbudget hoặc logical/physicalattempt budget. Giữ toàn bộ receivedresponse,
request và unknownattempt history;chỉ gọi các logicalslots chưa có response,
retry trong cap gốc. Inflightresponse chưa hoàn tất khi dừng có thể làunknown;
báo chi phíunknownriêng,không reset attemptcount hoặc gọi lại receivedresponses.

Mức8áp dụng cho reference/domain và PUTevaluation trên mọiarm;nativecachekey có
timeout nên tách với3s. Không reuse nativecheckpoints3s;nếu đã có nativecheckpoint
thì early override phải bị reject trước khi tạooutput. Source sharedprompt cũ
có guidanceexecutionunder3seconds vẫn giữ để không thaygenerationtreatment giữa
chừng;execution config thực tế8giây được report minh bạch. Frozen cohortbasepass
eligibility vẫn là cohort đã có,không sinh/score lại cohort writer/base tests.

Snapshot mới/preview/sourceguard ghi timeout8 và amendments beforefirstnative
execution. Không sửa oldmanifests để giả vờ đã chạy8s. Mọi old/new flowrecord
có metadata/artifact lýdo và links,actualresults vẫn pending. Hai endpointprivate
vẫn tách như user yêu cầu,không đổi URL/key vàoPrefect. Nativeevaluation lock
chunggiữnguyên. New output phải rebuild rootmanifest dưới settings8,không copy
manifest3s;inputs/hash/request/response copyđúngbytes và immutable replay ởcuối.

## 2026-11-09 — V2 refinement + soft examples; authorized delayed smoke24

User yêu cầu implementv2 cho EP+BVA vàDecisionTable,kết hợp behavioralrules/
inputdependencies,fault-hypothesisclassrefinement,representativemembership và
redundancy theo distinguishingfaults;DTconditions có thểderivedpredicates với
mộtparameter,orderedactions/feasiblecombination/mergecorrectness. Userchọn
**smoke6fourarms24calls**,chỉ chạy khi hai currentfullrunscompleted. Không chạy
fullv2 hoặc thêmLuna inference. “Luna không đạt90%” làtargetkhó vừa,chưađo;
không ghi thànhempiricalresult.

Arms:ep_bva,ep_bva_v2,decision_table,decision_table_v2.Cohortboundary_smoke
HumanEval0/5/18/81/99/120,1representativePUT/task;20inputs/task/arm,
1completion/task/arm,max24logicaltester calls/480inputrecords,4096completion
cap/call chung4arms,8192context,temp0.7,inputseed314159+task,reference271828+task,
nativetimeout8s,correctedHumanEval+reference2runs,confirm_first_failures.PUTs,
basecalls,spec/domain vàvisiblecontext jointlytokenized/trim cho4arms. Reference
oracle sauglobalfreeze,expectedoutputkhông doLLM,samecache/scorer. Physicalretry/
unknown/keepalive báo riêng;completionupperbound98,304tokenskhôngphảiusage.
Primarypairedcomparisons v1-v2 trong từngtechnique;cross-technique làdescriptive.
V2 thay cảinstruction+example;khôngclaimcôlậpriênghypothesis hoặc fewshot.

MỗiV2techniqueguidance8lines +1softproductionexample113words +compactoutputnote.
Optionalclass/rulefault_hypothesis ghi plausible spec-supportedmistake,liênkết
bằngcovers;khôngconfirmbug,khôngexecutehypothesis. V1khôngnhậnexample/note,
newoptionalfieldexcludedwhenNone đểgiữshapev1. No forced7stepreasoning/fulltable.
V2examples độc lậpbenchmarks theo nguồnproduction đượcpincommit/SHA256:
packaging713d0d78924ab2686c513dde058ce6aafc63e766 prereleasefallback saufilter;
Werkzeug5f11cd39b40ac03296ab7db446bfb0a737d77590 HTTPpreconditionprecedence/
methodstrongweakETag. 10checks trênunmodifiedsourcePASS;109localdatafiles
keywordscan0hits,khôngclaimuniversalbenchmark/pretrainingabsence.Licenses,
provenance,scope vàverification ởfinal/research/testing_arm_examples/.

Precedent v31faulttemplate18vs15/33(p≈.38,mộtwin doschema),v34placebo rulekhôngđạt;
hypothesis→test khôngphảiý mới. V2khôngreimplementpaper/mutationranking,
chỉspec-basedrefinement đểđánhgiá. Semanticgrounding/inputmembership chưa suyra
bằngmachine tiếp tục pending;catalogueinvalid khôngrejectvalidinput.

DelayedflowdependsBOTH43c7061b-38c6-4bbb-8c5a-6da366d337f9 và
d3a095ba-e5d2-46a4-bbe8-44deebdb6073. Prepare vàfreeze source/config/cohort/
soft_examplesJSON/privateendpointBEFOREwaiting,sourcehashincludesJSON.NOV2
model/tokenizer/nativecalls khiwait. Chỉlaunch khiAPICompleted +savedstatuscomplete,
evaluated_tasks==total_tasks,resultdigestsourcehash/replayPASS cho cảhai.
Failed/cancelled/crashed/missingproof thìblockwithreason,khôngstartworkload.
Waitpoll30s,updatecùngprogressartifactID,samefollowupflowrecord,atomicdispatcher
claim chốngduplicate. Worktreeedits sauprepare không đổi frozenworker.
Khôngtakeover/dừngcurrentruns,khôngretunetheooutputfullđangchạy.

### V2 prelaunch readiness receipt — 2026-11-09

Independent reviewer v2_final_review GO:JSONassetcopy/hash/frozenload,v1control,
optionalhypothesisfield,v2composition,24callbudget và BOTHCompleted+savedfinal
proof gate đềuđạt;4v2fixtures+6followuptests độc lậpPASS.Rootfullregression501PASS/
2isolated-envskips;11isolatedorchestrationtestsPASS riêng,v1saveddecode6tasksparity
PASS,10pinnedlibraryexamplechecksPASS. `git diff --check` PASS. Chưa cóv2model/
tokenizer/nativeworkload khi ghi receipt;được phép đăng ký mộtfollowuprecord
chờ hai fullpredecessors theo userinstruction. Sourceconfigexamples freeze trước
wait;khôngrereadmutableworktree lúcstart.

## 2026-11-09 — user-authorized Plain-guidance rerun, then V2 during evaluation

User yêu cầu chạy baseline trước với đúngguidance của Plain,rồi chạy smokeV2
khi baseline-rerun đang chấm. User cung cấp endpointQwen mới trongcùngturn,
servedmodelqwen3.5-27b-awq;không dùng model/backendCCG khác từđườngdẫnMac
khôngtồn tại trênhostLinux. Endpoint/keys giữprivate,không ghi vàoPrefect.

Baseline-rerun target là guidance-only comparison so vớiDirect77source
console_resume_43c7061b-38c6-4bbb-8c5a-6da366d337f9:cloneconfigexceptarms=['plain'],
giữ cap2048/context8192,temp.7,inputseed314159/reference271828,timeout8,
20inputs/task/arm,full164records/157eligible/1454PUTs,max157logicalcalls/3140slots.
Copy đúngbyte source packet.json đểcùngcommonprompt/visiblePUT IDs/order,
không tái trim theo1arm. No oldresponse/testexpectedoutputs đượcimport vào
newgeneration. Request chỉthêmPlaincue `No additional analysis packet. Choose
useful new tests from the information above.` vàoDirectemptyguidance.System,
data,seed,samplingcap giữnguồn. Ghi originalpacketprompt_tokens làhistorical
metadata;actual request đượcmodeltokenizer kiểm lại trướccompletion. Modelserved
alias giốngkhông chứng minh2serversloadedweights identical;khôngcausalclaim
chắcchắn guidancekhi stochasticregeneration/backendexecution cóthểkhác.

V2đã tựstart theoauthorization cũ khiendpointrevive,nhận4responses/task0 trước
lệnh reorder. Đãdừng117ba63bworker ởgeneration trướcnativeeval;oldsource/frozen
examples/4responses/attemptledger giữnguyên. Newcontinuation giữ4receivedslots,
chỉ chạy cònthiếu trongoriginal24logicalcallbudget;inflightunknownhistory
khôngreset. Prepareclonemới,trướcwait,khôngsửav2treatment/cap4096/timeout8.

V2continuation gate mới:baseline APIRunning evaluation hoặcverifiedCompleted,
configsourceguard,allgenerationrecords finished,generation_frozenhashes khớp
actualinputs,khôngstartV2khi baselinecòn sinhinputs. Khi gateđạt,V2generation
được chạy trênGPU tronglúcbaseline nativeevaluation;sharednative lock giữnguyên
nên V2evaluation chờ baseline nếu cần. BaselineFailed/Cancelled/Crashed thìblock,
khôngstartV2. Waitingpoll<=30s,sameprogressartifact;noextra childrun/duplicate.
Oldrun117baFailed phản ánhintentionalreorder,không phải efficacyfailure.

No newbaseline/V2responses were read when registering this amendment. Both new
outputs giữsource links,request/response immutablechecks,sourceguard vàreplay
beforeCompleted;reportsactualtokens/unknown/reusedresponses vàscientificlimits.

### Controlled rerun readiness

Original Direct frozen runtime vàpublicpackets được copybyte-for-byte trong
newoutput;configfresh chỉđổi selectedarm=plain,giữcap2048.Nativeoracle/reference
source cũnggiữnguồn,sourceruncomplete/sourceguardPASS trướccopy.NewSourceSnapshot
bỏstalehashes fresh-runtime,traversehashclone vàpacket copies;preparerdriver có
sourcecopy/hashriêng trongreceipts.Khôngimportresponses/inputs/oracles vào
newbaseline.Bothdriver helper và V2phasegate đượcindependent reviewerGO sau
fixRunning-before-outputexistsrace;9isolatedsequencefixtures+5dispatchfixtures
PASS. Gatefailclosednếufreezehashmismatch,missingtasks hoặcfailedbaseline.
Source/sourcepacket/userendpointreadiness đã kiểm trướcnewgeneration.

## 2026-11-09 — user-requested union input evaluation (post-hoc replay)

User yêu cầu gộp inputs của3arms vàevaluate. Scope:Plain/EP+BVA/DT từ CÙNG
completedfullsourced3a095ba-e5d2-46a4-bbe8-44deebdb6073,khôngmixPlainrerun,
khôngsinhnewcombinedtechnique/LLM. Source đã thực thi reference và mỗiPUT trên
chínhglobaldeduplicatedunion pool,sauđófiltertheoarm;do đó evaluation mới
materializearmunion và replay đúngnativecheckpointpool,khôngchạy lạicùngnative
workload chỉđểghi record. Userđãđượcgiảithích mode này trước replay.

Đã nhìn source outcome trong auditpost-hoc:unionexpected109/1454PUTs từ6344
uniquevalidinputs,sumarmvalidmemberships7916 nên1572duplicate memberships.
Khôngpretendprospectiveblindedexperiment.Rawdecoded8904records referencevalid/
base/dedup→6344;maxactual59/task,cap60 so với20/task/arm.Khôngclaimhigher detection
làgainởmatchedbudget. Matchedrandomsubsets dùngexistingReportingStage.compare,
post-hocdescriptive. Generationupstream471responses/1,598,499knowntokens giữchi
phíriêng;newmodelcalls0/newnativecalls0khôngnghĩaupstreamgenerationfree.

ReplaydùngexistingReferenceOracleStage vàPutEvaluationStage trênREADONLYsource,
kiểm inputfreeze/reforacle/PUTresults giốngsource và2observationconfirmations
cho every1454PUT. Addunionattribution phải giữsource nativepool exactrange,
uniqueinputkey/noorphan;missingcache fail beforeexecutor. Task/spec/domain/cohort,
stage/cachecode vàcorrectedreference giữsource. Timeout8s,inputseeds/scorer như
source. Uniongeneratedinputartifact không chứaexpectedoutputs;oracleartifact
riênggiữreferenceoutputs.Global/sourcefreeze+inventorybefore/after,materialized
results+checkpointcopy hashes vàimmutable replayrequired. Sourcecode/outputs/
checkpoints nguyên. Newoutput+Prefectrecordriêng,reportVIkind/denominator và
upstreamcost;không tựlaunchbenchmarkhaymodelrunbổsung.

### Union replay review receipt

Independentunion_evaluation_reviewGO:all1454nativeobservationsverified,4new
engineeringtestsPASS,actualsourceTask0shared-stage readonlyreplayPASS. Added
checkpointcopy sourceSHA==targetSHA receipts+replaycheck;newuniondriver/wrapper/
sharedmodules sourcecopy+hash andnumpy/scipy/pydantic/evalplusversionsrecorded
beforeevaluation,livecodehashcheckedagainatend. Root5dispatchtestsPASS.
Expected109/1454isalreadyknownposthoc,notnewprospectiveoutcome. Sourceguard+
fullsourceinventorybeforeafter+materializedimmutable replayremainrequiredbefore
PrefectCompleted. Noendpoint/modelinference ornativeworkloadrerun.

## 2026-11-09 — user-authorized single combined EP+DT+BVA arm

User làmrõ muốn mộtarmgọi đủ3kỹthuật,khôngunioninputs. Chọn existing
`ep_dt_bva`:mộtguidance EPclasses→DTconditions/feasiblerules/ordered-actionmerge
→normalBVAclassedges,single-fault,mộtcompletion/task với classes/boundaries/rules
catalogue vàmộtdanhsáchinputs. Khôngloadoldinputunion,khôngthêmV2examples/
fault-hypothesisinstructions ngầm;không chạy3armrồigộp.

ScopefullHumanEval nhưfullrun/union trước:164records,157eligible tasks,
1454base-passPUTs,arms=['ep_dt_bva'],20inputslots/task,tối đa157logicaltester
calls/3140inputslots,4096completiontokens/call,8192context,temp.7,inputseed314159+
task,referenceseed271828+task,nativetimeout8s,correctedHumanEval+reference2runs,
confirm_first_failures scorer. Modelqwen3.5-27b-awq.Keepalive/unknown/physical
retrytínhriêng.Trongrunmớivisibility đủcontext được tokenize theo combinedprompt,
khôngclaimidenticalpacketvớiprior3armjointtrim;nếu so crossrun cần ghi confounds.
Không sinh thêmPlaincontrolcalls,newrun singlecombinedarmđúnguserrequest.

Newgeneration→globalfreeze→domain/reference→cataloguemeasurement→PUTevaluation,
sourceguard/immutable replay/reportVI trướcCompleted. Catalogueinvalid khôngloại
inputhợp lệ;formaltechnique/semanticgrounding vẫn cần audit. Khôngclaimphươngpháp
đúngchỉvì modelxuất3cataloguesections hoặc chỉvìunion109trướcđó.Newoutcomechưacó.

Independentcombined_arm_prelaunch_reviewGO;offlineone-callfixture vàbudget
fixturePASS,52targetedengineeringchecksPASS (trước thêm presetdefinition cuối).
Endpointreadiness cảhaiprivaterouteshiệnHTTP404,0newgeneration. Submit một
Prefectrecordprepared/waiting_endpoint,khôngsubstitutemodel/backend,khôngcopy
oldresponses. Userđãđượchỏi activeendpoint. Sourcecode/configsnapshotriêng trước
firstgeneration;khôngautolaunchbenchmark khácsaucombinedrun.

## 2026-11-09 — User-authorized full v2 after current combined v1

User yêu cầu register/schedule full v2 với endpoint hiện tại, sau ETA v1 cộng
30phút. User xác nhận scope HAI arms đã smoke: ep_bva_v2 và decision_table_v2;
không tạo combined-v2 mới, không thêm Plain control hoặc solver. Cohort full164,
157eligible tasks/1454eligible base-pass PUTs,7cohort skips;20inputs/task/arm,
314logicalcalls tối đa,6280inputslots,4096completiontokens/call,context8192,
temp0.7,inputseed314159/reference271828+task,timeout8s,confirm_first_failures.
V2 giữ instruction+soft examples như smoke; không retune theo task outcomes.

Schedule receipt ghi observed progress và rolling20response cadence, generation
ETA, evaluation allowance60phút (ước lượng, historical full9–118phút),buffer30phút,
và not_before_utc làm tròn lên5phút. Đây là estimate, không bảo đảm v1 đã xong.
Workload v2 chỉ launch sau BOTHdeadline và predecessor57d6601b-94a6-42d8-a67f-
0d75160649bbCompleted có saved nativeevaluation/sourceguard/replayproof.
Predecessor failed/cancelled/crashed thì block,không tự rerun/resume.

Đăng ký một followupPrefectID; dispatcher chạy ngay CHỈ để freeze code/config/
cohort/examples/private route và chờ. UI flow Running/Waiting; actual workload
schedule trong not_before_utc. Copy private profile của v1 qua existing worker
prepare; opaque routeidentity phải trùng,không lưu URL/key trong artifacts/Prefect.
Chưa model/tokenizer/nativecalls trong lúc chờ. Không sửa v1worker/source.
Newrun haiarms jointlytrim riêng; không claim cùngpublicvisibility/packets với
v1singlecombined hoặc full3arm cũ. So efficacy phải báo confounds này.

Independent review_v2_full_schedule GO;13followup/dispatch testsPASS. Optional
not_before gate không đổi behavior của followups cũ khi fieldNone; fake-clock
fixture giữ ready-predecessor chờ deadline và timezone validationPASS.

## 2026-11-10 — User-authorized tool sampling smoke12 after v2

User yêu cầu đăng ký tool pipeline mới sau khi kiểm/tiếp tục full v2, sau đó chọn
rõ **smoke12 tasks**. Chỉ một run smoke12 này được cấp quyền; không tự mở rộng
full164 hoặc chain thêm benchmark sau kết quả.

### Scope, selection và model budget

Dùng union hai bộ **spec-selected smoke6 có sẵn**, boundary và equivalence,
không xem detection outcomes để chọn task/PUT. Task numbers cố định:
`[0,5,11,18,22,26,51,81,85,99,120,137]`. Giữ representative PUT đã freeze
trong hai parent cohorts, **một PUT/task**, không sinh/rewrite/rerun writer.
New cohort `final/out/development_groups/testing_tools/smoke12/cohort.json`,
SHA256 `2813736f86806fe5116c9f7a3b2704e6bb3b7a2a2d2be6c7c6e1e8e75ae9d40e`.
Parent hashes và selection rule nằm trong development_selection. Twelve task
records, 12 eligible PUTs. Đây là engineering smoke, không efficacy benchmark
đại diện toàn HumanEval, không tune selector từ diagnostic cùng các task này.

Arms: `tool_direct`, `tool_hypothesis`, `tool_hypothesis_z3`,
`tool_hypothesis_extra`, `tool_planner`. **Một preparation completion/task dùng
chung**, cùng direct/base seeds và cùng initial Hypothesis pool (trừ direct-only).
Tối đa **12 logical model calls**, **4096 completion tokens/call**,
**49152 completion tokens tổng cap**; context8192, temperature0.7,
inputseed314159+task, referenceseed271828+task, model`qwen3.5-27b-awq` như v2.
Keepalive/physical retries/unknown usage báo riêng; không reset retry ledger.
Một arm tối đa20 final inputs/task; cả run tối đa1200 final input slots.
Direct control từ preparation mới, không phải prompt Plain cũ.

### Tool/native budgets và controls (đã chốt trước mọi workload)

Mỗi task: initial Hypothesis64draws/2s shared; Z3 bổ sung tối đa12queries,
250ms/query, total3s; extra-Hypothesis control64draws/3s (cùng wall cap3s,
actual time không mặc nhiên matched); allpairspy tối đa16rows, Hypothesis tối
đa8draws/row, tối đa12solver queries (cả feasible-DT obligations và rows),
planner total5s. Không shrinking. Budget checks hợp tác ở draw/query/row;
Z3 có query timeout riêng, không claim OS-hard deadline.

Suite selector giữ policy trong proposal: native verified coverage, feasible-DT
unique witnesses, greedy new targets, rare target, fault rationale, stable
canonical hash; diversity spec-only, membership unknown/error vào cuối.
Z3 giữ toàn domain/context/target, integer/bool exact subset; unsupported không
bỏ constraint. allpairspy strength2 không thay thế DT obligations.

Diagnostic sau **global freeze**, audit cap **256 unique candidates/task/arm**,
bao gồm frozen selected suite trước, stable hash cho phần còn lại. Tối đa15360
pool candidate slots cho cả12tasks×5arms, execution cache có thể giảm actual
native work. Native timeout8s/input; corrected reference hai observations,
`confirm_first_failures` scorer. Random control seeds `[11,19,29,37,43]`, cùng
pool, tối đa20inputs/seed. Pool bị cap thì ceiling null/lower bound, generation
gap pending; parse-interface gap unknown nếu chưa có authorized repair evidence.
Không dùng oracle/PUT outputs trước freeze hoặc sửa suite sau diagnostic.

### Schedule, publication và completion

Một Prefect followup record sau full-v2 `4ad4ea3a-56d4-4bd7-b039-835978e62d68`
**verified Completed** (native evaluation đủ, sourceguard + read-only replay)
AND **not_before `2026-11-10T01:20:04Z` (08:20:04 Asia/Ho_Chi_Minh)**.
V2 đang giữ cùng worker/flow và timer theo endpointETA20phút; không restart
hoặc tạo duplicate v2. V2 failed/cancelled/crashed thì block followup, không
bypass predecessor gate. Not-before là mốc sớm nhất, không phải ETA kết thúc v2.

Prepare snapshot code/config/cohort/private route ngay khi đăng ký rồi chờ;
route mới copy từ private profile của v2, xác minh opaque endpoint identity
trùng, không in/lưu URL/key trong repo/Prefect. Không reload listener hoặc đổi
snapshot của v2. Chưa tokenizer/model/nativecalls của smoke12 khi chờ gates.
Chỉ Completed sau native evaluation + pool diagnostic + sourceguard/immutable
replay/report tiếng Việt. Metric chưa có là pending, không điền0. Report funnel,
parse primary/multi-label, validity/membership, coverage/tuple feasibility limits,
detection wrong-value/exception/resource, pool/random/selection loss và actual
calls/tokens/time; input và PUT count cùng mẫu số rõ ràng.

### Smoke12 prelaunch review và interface amendment

Independent `review_tool_sampling` xác nhận union12/cohort/preview/gates/budgets GO.
Phát hiện task22 annotation `List[Any]` làm adapter chuyển preparation hợp lệ
sang direct fallback. Sửa coarse typing `List[Any]`→`list` (giữ elements tùy ý,
không thêm ràng buộc ngầm) trước snapshot/first inference. Regression offline
RED→GREEN với heterogeneous list và Hypothesis receipt. Không thay task/scope,
prompt, seed, budget, reference hoặc any historical outputs.

### Smoke12 schedule amendment — endpoint404 và v2 readiness timeout

2026-11-10 01:45UTC: original v2 flow4ad4ea3a FAILED sau readiness deadline6h,
worker status interrupted/TransportError(models,HTTP404),0responses/0attempts.
Theo lệnh user “chưa thì cho chạy lại”, tạo đúng **một continuation v2** từ source
cũ, giữ frozen runtime/config/prompt và toàn bộ retry/checkpoint; không làm lại
response đã nhận (hiện0). Private route tiếp tục từ source, không đổi model/backend.
Smoke12 predecessor chuyển sang **continuation ID đăng ký trong receipt**, không
trỏ run4ad4ea3a đã failed; vẫn cần verified Completed và originalnotbefore01:20:04Z.
Đây là continuation của cùng full-v2 scope, không cấp thêm run/benchmark mới.
Endpoint check hiện HTTP404; cả continuation và followup phải report pending,
không claim workload đã chạy. Không tự nối thêm continuation nếu lần này thất bại.

### Smoke12 route/schedule amendment — user yêu cầu chạy ngay trên server riêng

User cung cấp endpoint OpenAI-compatible riêng, model `qwen3.5-27b-awq`, và yêu
cầu smoke12 chạy ngay. Lệnh này thay gate chờ v2 của smoke12. Chỉ chuyển smoke12;
v2 tiếp tục nguyên private route/worker/config hiện tại. URL chỉ ở private
profile ngoài repo, không trong config/Prefect/report/memory.

Followup chờ993dc0d6 chưa có attempt/response/nativeworkload: cancel trước
launch và giữ output/metadata; tạo đúng1 benchmark thay thế cùng config/scope,
budget12sharedcalls/5arms/suite20 và cùng source runtime. Ghi supersedes/source
run trong receipts/Prefect. Không cộng budget, không có2smoke workers hoạt động.
Endpoint `/models` phải xác nhận đúng model/context trước launch. Generation có
thể chạy song song v2 vì opaque endpoint identities khác nhau; nativeevaluation
vẫn shared lock serialize. Freeze/reference/audit/scorer/report giữ nguyên.

## 2026-11-10 — Contract repair, không cấp thêm workload budget

Sau smoke12 bị invalid12/12preparation, user cho phép sửa contract/validate saved
responses/offline tool proofs và chuẩn bị smoke phù hợp. Protocol mới
`tools-ep-bva-dt-v2-structured` thêm JSON Schema native decoding + local strict
validation; không tự diễn giải prose thành constraints hoặc drop unsupported domain.
Prefreeze treatment gate ngăn reference/PUT evaluation khi preparation/tool không
được exercise. Notapplicable/notneeded không được tính là evidence tool effect.
Recorded/Cached request identity bao gồm response_format, old unstructured requests
không đổi. Chưa benchmark/model/native-evaluation rerun trong scope sửa này.

Independentreview hai mustfix (sharedHypothesis evidence ởcombinedarms; boolean
operands củaand/or) đã reproduceRED→GREEN. Mixed int/bool/sampling/strategy support
không mở rộng vô căn cứ. Offline synthetic fixtures gọi API thật Hypothesis/Z3/
allpairspy để xác nhận candidate/native replay/row realization; không gọi reference/
PUT hoặc tính detection. Audit saved12responses giữSHA256/bytes trước-sau;
0/12schema-valid nên khôngrelabelold1/12PUT thành hiệu quả tools.

`INTEGER_TOOL_SMOKE_PROPOSAL.json` chỉ đề xuất tasks13/44/49 từspec/signature/
trustedcontract,không xemdetection outcomes. Chưa chọncohortPUT/budgetexecution,
chưa submitPrefectrun. Cầnuserra lệnh rõ run mới trước inference/evaluation.
Old smoke runtime/outputs/response và livev2snapshot giữ nguyên.

## 2026-11-10 — User-authorized repaired smoke12 on newly supplied private route

User cung cấp endpoint mới và ra lệnh “chạy đi” sau contract repair. Chạy đúng
smoke12 cũ (tasks0,5,11,18,22,26,51,81,85,99,120,137;12frozenrepresentativePUTs),
5arms,20inputs/task/arm;KHÔNG tự đổi sang integer proposal13/44/49. Đây là
repair rerun của sourcea467891a,sourceoutputs giữ nguyên,newPrefectrecord/output.
ModelQwen3.5-27B-AWQ,completion4096/context8192,temp.7,seeds/timeout8scũ;
12sharedpreparationcallsmax,49152completiontokenscap,toolbudgets unchanged:
initialHyp64draws/2s,Z312queries×250ms/3s,extraHyp64draws/3s,
planner16rows×8draws+12solverqueries/5s,audit256/task/arm,random11/19/29/37/43.

Dùng protocoltools-ep-bva-dt-v2-structured với native JSONSchema response_format,
local schema/boolean validation, shared-Hypothesis evidence và prefreeze gate.
Nếu preparation/applicable tool không được exercise, không chạy oracle/PUT và
không gọi run đó là valid comparison. Z3 phần lớn khôngapplicable trên smoke12
list/string/float;report riêng,khôngclaimZ3efficacy. Integerproposal vẫn chưa chạy.
Chỉ12sharedcalls của rerun này,khôngautofull hoặc tự mở benchmark mới.

Prelaunch endpointmodel/contextPASS qua GET /models,0completion cho readiness.
85tool+transport regressionPASS. Independent contractreview trước đó đã sửa
hai mustfix,full569+isolated23checksPASS. Snapshotcode/config/cohort/private route
trướcgeneration,credentials/URL chỉprivateprofile,khôngrepo/Prefect. V2khôngđổi.
Globalfreeze→reference→PUT+poolaudit→sourceguard/replay/reportVI trướcCompleted.
Newreceipt ghi source run và budget;chưa có detection/coverage ởlúcregister.

## 2026-11-10 — User-authorized weak-subagent preparation contract smoke

User yêu cầu chuẩn bị prompt rồi dùng subagent model yếu nhất có thể chọn để
thử đúng contract và xem kết quả. Chọn explicit `gpt-6-luna`, reasoning low,
4 independent fresh subagents,1attempt/task,max4attempts; không dùng inherited
model/context,khônggửisavedanswers. Tasks44(integerjointbaseboundary),11(binary
strings/equal-length),120(list+k jointdomain),137(polymorphicnumericrepr) chọn
bằngspec/signature/trustedcontract,khôngbằngdetectionoutcomes. Prompts/messages/
JSONSchema đúng pipelinev2-structured đónghash trướcdispatch tại
final/out/tool_contract_luna_smoke_20261110/. Model nhận schema dạngtext,không
có native guided decoding ởsubagenttool;phải ghi rõ khác với endpointQwen.
Outputcap4096tokens là instruction,subagenttool không exposehardtokenlimit;
actualusagechưacóthìunknown/pending,khôngghi0.

Mỗi agent chỉ đọc assignedprompt và viết nguyên JSON response,khôngchạyvalidator,
khôngxemcode/answers/taskkhác,cấmendpoint/inference/PUT/referencecall. Rootvalidate
rawresponseJSONschema,executableexpressions,signaturetypes,membership vàrealtool
constructors trongbudget đãchốt64draws/2s,Z312queries250ms/3s,extra64/3s,
planner16rows×8draws+12queries/5s;khôngnativebenchmark/reference/PUT execution.
No repairs/secondattempt trongcomparison này. PrefectexternalrecordreuseflowID
vớiconfig/progress/outcomes/report;metricschưađocònpending. Cầnpublishactual
contract failvàunsupported,khôngclaimdetectiongainhayweakmodelrankingđịnhlượng.
Khôngsửaprompt/runtime/candidateoutputcủarunQwenhiệnđangchạy.

## 2026-11-10 — Domain-authority repair, offline validation only

User yêu cầu sửaLuna4failures và“continue”;pastedPrefecta7failuređượcđọc nhưcontext
cùngtask,khôngcấpnewrunbudget. Protocolv3 pintrusted admission domain,independent
admissiontypes và recomputedprefreezeauthority. Các purehelpers/dependentlenbounds
thêm đúngfailuremodes. Compiler supportall12smoke admission contracts trongunit
checks,unknownclause/resource/name-shadowingfailunsupported. Noarbitraryexec,
khôngsửaoldrawanswers hoặcoldrunruntime,khôngautocomprehension/proserepair.
Reviewfindingscachebypass/inferredtypenarrow/ASTdepth/builtinshadowing đãfixRED→GREEN;
expandedcompilerreview bắt eagerListComp-range và importmathshadowing,đãchặn bằng
regression. Bốncorrectedfixturepreparations gọiHypothesis/membershipthật offline,
khôngPUT/reference/benchmark ornewLLMcalls. Chưa cóoutcomes của repairrunv3.

Faileda7abfb17diagnosis:12/12responses received,33855tokens,gateFalse trên12task
invalidpreparation,0oracle/PUT/noglobalfreeze. Metricsdetectionpending,không0fake.
Publishedsame-flow failureaudit;giữsource/checkpoints. Newrun cầnuserquyếtđịnh.

## 2026-11-10 — Exact user-requested gpt-5.6-luna low smoke4 after v3 repair

User yêu cầu test lại đúng`gpt-5.6-luna`,reasoninglow (khôngthaygpt-6-luna).
Same4cases44/11/120/137,onefreshsubagentattempt/case,max4,0repair;currentv3
PREPARATIONmessages+trusteddomain-pinnedJSONSchema đónghash trướcdispatch,
khônggửisavedanswers/validatorfeedbacktớiproducers. Output<=4096tokensinstruction,
toolhardcap/actualusagekhôngexpose thìunknown,khôngghi0. Localcapabilitycache
cóexactmodel+low;orchestratormodelselection phải đúng trước nhận kết quả.

Sauoutput:strictJSON/schema/pinned-domain/expressionvalidation rồirealtool
constructors cùng per-taskbudgets đãcó,manualsemanticchecks từspec/domainnative;
khôngbenchmarkendpoint/PUT/referenceexecutions. Khôngautofull hoặc sửarawresults.
Textschematrongsubagentkhôngphảinativeconstraineddecoding. Confound khác model
vàpromptso vớiLuna6trướcđó:khôngclaimmodelranking hayefficacy. RecordPrefectriêng,
metrics pending cho đến kiểm xong. Source:final/out/tool_contract_luna56_low_v3_smoke_20261110/.

## 2026-11-10 — User-authorized applied signed-controls Luna smoke12 + bug evaluation

User yêu cầu thực sự áp dụng research/sửa generic tới passcontracts và tìmgenuine
bug;khôngtask-ID/task-specificbypass. Giữ ORIGINALsmoke12tasks/12representativePUT,
5arms/final20inputs/toolcaps64initial2s,Z312query250ms3s,extra64/3s,
planner16rows8draws12queries5s,audit256,random11/19/29/37/43,timeout8s.
ExactGPT5.6-Luna low fresh prep12+blindreviewer12+max1repair/case12,khôngQwenAPI.
Reviewer chỉthấyspec/trustedsource/targetdescriptions,khôngpredicate/candidate
inputs/PUT/referenceoutputs. Signedcontrolgategeneric,theoexpectedmembership,
khônghardcodename/ID;unknownkhôngpass,domaininvalidnegativekhôngsemanticproof.
Genericdistinct_countvàliteralintentinstructions áp mọi sequence/alphabet,không
vá riêngbinarytask. Artifactprompt/case controls/sourcehashfrozen trước evaluation.

All12inputs đượcfreeze trước correctedreference/PUT execution,confirmfailure,
sourceguard/cache/reportVI+Prefect1record. Không chỉnhselector/inputs sau outcomes
để cưỡngbứcbug. Mộtbug chứngminh validfrozeninputrevealPUT,khôngcausalgaincủatools.
CaseskhôngsupportZ3/planner báoNA/notneededkhônggiảexercise. Chi phísubagenttokens
khôngexposethìunknown,không0. Khôngautofull164/newpaperreimplementation.

### Signed-controls pre-evaluation repair amendment

Initial12prep+12blindreviews+4repaircases=28caseattempts. Một repaired candidate
vẫn hiểu Boolean overlap helper thành numericcount và dùng futureparam bound;
chưafreeze/chưaoracle/PUT. Cấp thêm1contract-onlyrepaircase cùngLuna low trong
max36totalcaseattemptsđãchốt,khôngdùngdetectionfeedback. Addgenerichelperreturntype
validation/prompt và nofutureparamdependency đểfixsharedcause,khôngtaskIDpatch.
Originalattempts/controls/labels giữ nguyên. Plannedtotal29caseattempts.

### Fixed smoke evaluation scheduling amendment, after freeze before native outcomes

Global12suitefreeze+118signedcontrols đãPASS; chưa nativeevaluation của lượt mới.
V2fullrun đanggiữ console native lock (35/164taskevaluated tại kiểmtra),host16CPU/
load1~1.42. Lượt smoke supplied-input CLI dùng freshbwrap/per-inputcache isolation
và một nativeworker riêng để hoàn tất user-requested bugcheck, đồng thời vớiv2;
không đổi console/V2lock/worker hoặc sửaoldoutputs. Đây là scheduling amendment,
khôngbudget/cohort/selector/oraclechange. Không creditresource/timeout làm“ra bug”;
chỉ wrong-value được hai observations xác nhận và independentreference.

Read-only join với completedoldsmoke exactinputs/executioncode/refhashes saufreeze
đãmatch31selectedinputobservations và0confirmedPUT; khôngđổiinputstừ kếtquả đó.
Currentfrozeninputs/controlhashesgiữ nguyên; fresh evaluation tất cả12taskbằng
correctedreference và scorer cũ. Khôngclaimed benchmarkcausalgain từ thay đổiCPU
scheduling. Cache per-inputlocks vẫn giữ và no-model KeepAlive bị tắt cho supplied
preparations. Không có Qwen/liveendpoint/modelcall mới trong nativephase.

## 2026-11-10 — User-authorized test of the two prompt examples; no prompt changes

User: “thử trên mấy cái examples ... dùng cho vào prompt ... chỉ test thôi,
k sửa prompt”. Scope is the two existing soft-example domains: packaging version
filtering and Werkzeug HTTP preconditions. This is an in-sample diagnostic,
not a held-out benchmark or a new claim of method superiority.

Use exact GPT-5.6-Luna low, 2 fresh preparation cases and at most 2 independent
blind control-review cases, no repair/retry or model substitution. The current
ToolInputGenerator PREPARATION text/schema/helpers/selection are unchanged;
only task-specific spec/contract payload and thin invocation wrappers differ.
Reuse original smoke12 tool budgets, 20 final inputs/task/arm, all 5 arms,
8-second native timeout, two reference and two PUT observations. No full-pool
native audit in this small diagnostic. Invalid contracts/gates stop native work
for that case; do not patch prompt, runtime or preparation to manufacture a pass.
Freeze every generated suite/control before accessing oracle/PUT outcomes.

Reference: unmodified packaging713d0d78924ab2686c513dde058ce6aafc63e766 and
Werkzeug5f11cd39b40ac03296ab7db446bfb0a737d77590, already pinned for examples.
PUT: real upstream source before packaging fix48125006684b (parent1c368514d5d7)
and before Werkzeug precondition-order correction34e4c1c3cc67 (parentfbbbf74573dd).
Source archives/hash receipts are kept in the run directory. No synthetic
mutants or upstream-source modifications. Wrappers map JSON values to the real
APIs and normalize HTTP status/412; do not reproduce the library algorithms.
Werkzeug GET/HEAD precedence differences are separated from the old API's
documented absence of PUT support; do not count that missing feature as an
independent historical precedence bug. Invalid PEP440 inputs rejected by the
reference are reported, not credited as bug witnesses.

No buggy/fixed code, historical witnesses or oracle outputs are shown to the
producer/reviewer. Controls are finite semantic evidence, never NL-equivalence
proof. The original examples have been exposed in earlier prompts; no claim of
unseen-domain generalization. Record config/progress/results/report on one new
Prefect flow; 0 benchmark endpoint calls; agent token usage unknown if unexposed.
Output: final/out/tool_prompt_examples_luna56_low_20261110/.

Pre-native note for this diagnostic: independent read-only harness review has
0 must-fixes. Both Luna responses have empty targets; mechanical gates are ready,
but semantic evidence is absent/vacuous and will NOT be reported as a pass.
No blind target-review calls needed (actual0), no repairs. All suites frozen.
Native work uses one existing bwrap worker and an isolated copy of the existing
benchmark dependencies plus already-installed MarkupSafe; shared venvs untouched.
Small native test may overlap v2 on the multi-CPU host without changing its
worker, console routing or global lock. Resource outcomes do not count as bugs.


## 2026-11-10 — User-authorized Qwen test of same two prompt examples

User gives live Qwen3.5-27B-AWQ endpoint and requests run; same2packaging+HTTP
examples/scope/budgets, prompt/task payload unchanged from Luna diagnostic.
Critical instruction: collect/persist ALL LLM responses before ANY sampling/tool
execution; do not interleave generation and Hypothesis/Z3/planner. Phase1 makes
only2logical structured preparation calls (4096completion/8192context,
temperature0.7,seed314159+task,thinkingfalse); reviewed transport may retry at most
3physical attempts/logicalcall. Save every attempt/response before a response
collection barrier. Missing response blocks all tools, no semantic repair.
Phase2 only consumes saved responses; no fresh producer completion. Same5arms,
20inputs/task/arm and native2repeat/8s budgets; no fullpool native audit.
Original example task/reference malformed-version inconsistency is preserved
and reported, never counted as a PUT bug. HTTP PUT feature gaps remain separate
from GET/HEAD precedence bugs. No prompt/schema/helper/selector modifications.
No additional benchmark/tasks beyond these2; user chooses any next run.
Output final/out/tool_prompt_examples_qwen_20261110/. Report on one Prefect run;
endpoint stays process-only and is excluded from config/logs/memory/Prefect.

## 2026-11-10 — Full164 tool run, user requests overlapped producer/consumer

Latest user request explicitly supersedes collect-all barrier: while receiving
LLM response for the next task, asynchronously generate/evaluate the preceding
task to overlap I/O and CPU. Full164 run authorized, same cohort and5tool arms,
20inputs/task/arm,4096completion/8192context,temp0.7,inputseed314159/reference271828,
8s/input,confirm_first_failures,originaltoolbudgets/auditcap256,seeds11/19/29/37/43.
No prompt/preparation schema/strategies/selector changes or per-task bypass.

One sequential LLM producer persists request/response/attempt metadata, then
submits that task to one CPU consumer process. Consumer uses existing benchmark
stages, all5arms/gate/freeze before reference/PUT/audit, then read-only replay.
Producer never reads outcomes or adapts subsequent requests from them. Requests
are task-level, shared over all base-pass PUTs. Single native lock retained.
Freeze scope is per-task (all arms together), not global164; this is an explicit
scheduling/protocol amendment, not a claim of exact previous protocol parity.
Per-task gate failures retain artifacts and block that task's oracle; continue
other authorized task slots, never bypass failing admission/treatment.

Cohort164tasks,157eligible tasks/1454base-passPUTs; at preflight110eligible tasks
have supported trusted contracts,47are unsupported by current conservative
compiler. All164slots recorded,7cohort skips and47unsupported remain explicit;
no completion for unsupported contracts, no unconstrained domain substitution.
Thus max157logicalslots but current compiler permits<=110newpreparationcalls;
existingtransportcap3physicalattempts/logicalslot,unknownusagekept. Semantic
controls not supplied for full; semanticgrounding remains unproven and empty
targetsets must not be called semantic pass. Unsupported/gate blocked metrics
remain pending, fullrecord notCompleted if necessary evaluation is missing.

Immutable code/data/config/cohort snapshot prepared before first response;
private route outside repo/Prefect. Output:
final/out/full_tools_qwen_overlap_20261110/. New coordinator/tool_overlap.py only
changes scheduling/recording; reviewed shared samplers/algorithms unchanged.
No extra benchmark/cohort expansion or auto semantic repair after this run.

Prelaunch independent review found2coordinator races: duplicate producer could
overwrite owner state; observer could publish a stale report then mark terminal.
Fixed before any model/native workload, with RED→GREEN tests (4overlap tests).
Producer lock now covers first shared mutation through terminal write; lock
rejection leaves owner state untouched. Observer reads terminal status before
report aggregation. Frozen coordinator snapshot/hash updated before launch.


## 2026-11-10 — Control-flow concept module và exact Luna response smoke

User yêu cầu tạo module trong final để cố gắng thử uncovered branches bằng
concept/instruction, có thể đảo tool/LLM roles, và cho phép test response với
exact gpt-5.6-luna low. Đây là adaptation PANTA/HITS/PALM dùng coverage.py,
python-graphs, Hypothesis và original-source sandbox hiện có; không reproduction
paper engine hoặc claim method mới so v11/v13/v57/VR15.

Authorized smoke duy nhất:3authored fixtures early-return/short-circuit,
cardinality-after-dedup, accumulator-loop; tối đa2generation rounds/case,6logical
Luna calls tổng,16draws/concept/2sampling seconds,32candidate–PUT observations/case,
1baseline call/case; suite8/case, timeout1s/input. Model exactgpt-5.6-luna/low
qua CLI text response, không JSON-schema cưỡng bức, tools disabled. Output
final/out/control_flow_luna56_low_contract_20261110/. Không hidden tests,
canonical/reference/expected outputs hoặc functional detection evaluation;
không chạy cohort HumanEval/full benchmark. Native trace chỉ cung cấp domain,
status, executed lines/arcs; không actual output để model chép.

CLI không expose temperature/seed hoặc verified provider max-output cap;
completion4096 là requested/advisory, không claim matched sampling/API behavior.
Context byte-length guard conservative; actual CLI usage lưu khi có, không
điền unknown token/cost thành0. Một slot đã bắt đầu không tự retry khi timeout
hoặc unknown charge. Contract errors trong response đi vào vòngfeedback còn lại;
không sửa raw response hoặc dùng task-ID bypass. Source/prompts/config/cases
freeze trước model; metadata/run/artifacts ghi Prefect cùng1flow_run_id.

Independent read-only reviewer trước model smoke; must-fixes ghi amendment và
engineering tests trước outcome. Contract-ready = có source-bound concept và
ít nhất1round không schema errors; target coverage tính bằng native trace/domain,
không self-report. Predicate/model semantics vẫn hypothesis. Báo số input riêng
với số verified targets; không gọi fixture coverage là bug detection.

### Amendment trước Luna smoke: independent review

Reviewer reproduce3important issues trên authored engineering fixtures:
base calls[:32] làm nhánh ở call33 bị nhận nhầm missing; native C hard timeout
làm abort run; dedup bỏ source của concept mới ở round2. Sửa trước model:
replay toàn bộ recorded calls tới cap300/PUT, không silently truncate; missing
measurement/partial failure là unknown; singleton sandbox cho từng input và
control_flow hard-timeout receipt domain unknown/no coverage, infrastructure
failure thật vẫn raise; merge concept provenance và reuse trace khi duplicate.
Thêm4regression checks gồm native C timeout. Không đổi cohort/model/smoke budget.

### Amendment sau3response, trước remaining feedback slot

Smoke nhận3responses/0schemaerrors, nhưng audit raw loopconcept thấy predicate
`sum([1,2]) == 3` và conjunction chứa nó không nói về input xs. Target hit thật
không validate predicate. Giữ source/archive/raw response và kết quả v1 nguyên.
Sửa generic contract: mọi comparison clause phải reference input parameter;
relation unsupported được đểpredicate rỗng và native target check vẫn chạy.
Feedback phải còn chạy khi coverage đã đạt nhưng concept contract lỗi.

Chỉ dùng1lượt còn lại của loopfixture (lượt2/case), không rerun2case đầu hoặc
mở thêm fixtures: tổng4/6logical slots của authorization ban đầu. Output repair
ở source run/loop_predicate_repair, ghi source run và source hashes mới, giữ cùng
PrefectflowID. Không sửa input theo known bug outcomes; không functional oracle.


## 2026-11-10 — User-authorized Qwen endpoint control-flow smoke3

User cung cấp endpoint và ra lệnh chạy module. Chạy đúng3authored fixtures từ
Luna smoke: early-return/short-circuit, dedup cardinality, loop accumulation.
Scope current C1/C2; không tích hợp C3 hoặc mở benchmark trong run này. Model
exactqwen3.5-27b-awq, context8192, completion4096/call, temperature.7, seed314159,
thinkingfalse; tối đa2rounds/fixture=6logical calls. Existing checkpoint retry
policy cap3physical/logical (tối đa18physical attempts); received response không
regenerate. Tool/native cap32candidate–PUT observations/fixture,16Hypothesisdraws
/concept/round/2s,8selectedinputs/fixture,1s/native call và1baselinecall/fixture.

Output: final/out/control_flow_qwen_smoke3_20261110_154832. Source/runtime/cases
freeze trước completion; private per-run profile ngoài repo, không thay route
run khác. Model/tokenizer metadata preflight đã xác nhận,0completioncalls ở
preparation. Independent review runner trước launch, source snapshot/hash guard,
read-only replay. Dùng sharednative lock theo singleton và endpoint identity
để serialize generation cùng route/unknown; không restart/cancel run khác.

Đo concept response structure/bindings, native target hits và input yield.
No functional oracle/hiddenlabels: bug detection ngoài scope. Contract-ready
cần concept và latest round không schema errors; không tự coi target hit là
semantic proof. Báo fail/unknown thật, tokens/calls thật, giữ raw responses.
Prefect1record/source với config/progress/results/report tiếng Việt, verify API.
Không nối thêm run/fixture/benchmark sau smoke khi chưa được yêu cầu.

### Prelaunch review amendment
Reviewer phát hiện duplicate invocation có thể ghi failed đè status của owner
khi chưa lấy lock. Runner sửa chỉ ghi failure khi đã acquire lock và start marker;
duplicate test trong temporary directory giữ nguyên live status và0workload.


## 2026-11-10 — Scope superseded by explicit FULL164 authorization

User sửa: “à, chạy full luôn ấy”. Smoke Qwen draft chưa launch/0completioncalls,
được supersede; không chạy thêm3fixtures. Fullrun dùng frozen HumanEval164cohort
hiện có,1634generated/1465basepass;157eligible task/1454evaluatedbasepassPUT,
7generation-shortfall skips. Singlearm control_flow, không tạo Plain mới hoặc
regenerate cohort. Model exactqwen3.5-27b-awq,4096completion/8192context,.7temp,
seed314159,thinkingfalse. Input20/task,2adaptive rounds tối đa→314logicalcalls,
existing retrycap3/logical→942physical attempts;64candidate–PUT trace observations
/task≤10048,32Hypothesisdraws/concept/round/2s,6targets/task,trace1s.
Reference corrected HumanEval+v0.1.10, nativeevaluation8s, confirm_first_failures.

Output final/out/control_flow_full164_qwen_20261110_155408. Source/data/cohort
immutable snapshot, private per-run route ngoài repo. Current C1/C2 module;
C3chưa tích hợp, không đổi algorithm/prompt giữa fullrun. Per-task freeze trước
reference/PUT, generation producer không nhận evaluation outcomes. Một producer
sequential/adaptive và1isolated CPUevaluation worker chạy chồng lấp; shared
native lock cho traces/eval, opaque private per-route generationlock. Existing
full-tools route đã xác nhận khác endpoint; không cancel/restart/change route.

Independent runner review trước launch; sửa owner-status race và check protocol
freeze/read-only replay. Runlâu detach, Prefect1record/config/progress/report,
chỉCompleted khi đủ evaluation/replay/source verification; fail/skip nói thật,
metric chưa đo pending. Đây là fullsinglearm exploration; không matched efficacy
claim so Luna/Plain. Hết authorized run không tự nối thêm experiment.

### Fullrun prelaunch review amendment
Read-only reviewer bắt nested exclusive runlock/read-only replay conflict và
owner/child error-status gaps. Replay chuyển ra ngoài exclusive lock; owner
exception ghi terminalfailed, duplicate rejected không ghi sharedstatus; nonzero
child exit có phase-specific failure receipt. Regression duplicate+SIGKILL-like
consumerexit137 pass,0workload. Usage ghi unknownattempt/missingfooter counters.
Freeze runner/source/data/config hash trước launch; fullscope/budget giữ nguyên.

## 2026-11-10 — Bounded native tool agent operational smoke

User approves real agent with max4toolcalls and about4LLMturns, says fairness
not needed, prioritize working. Implement actual LangChain bind_tools/native
AI tool_calls, exposed sample_inputs/check_inputs/solve_inputs/submit_inputs.
Hard4physicalLLMrequests/task (SDKretry0, persisted unknown attempt blocks
resend), hard4toolattempts/task incl invalid/unknown/parallel/crashunknown calls.
Checkpoint tool model/ledger/result before next turn; partial resume replays
saved results, no repeat physical tool. Native stream must finish stop/tool_calls;
partial/truncated never executes. Tool inputs validated and membership sandboxed.
No PUT/reference feedback into agent; sampler feedback allowed. Finish cap20
selected inputs. Same trusted admission compiler, unsupported admission explicit.

Operational smoke selects HumanEval55 and64 because their previous responses
failed interface, not based on bug outcomes. Same frozen fullcohort/PUTsource,
2tasks×10expectedPUTs, at most8LLMrequests/8toolcalls total,4096completionrequest
cap/context8192,temp0.7,inputseed314159/reference271828,native8s,
confirm_first_failures. No new5armfairness baseline/poolaudit. Inputs freeze for
bothtasks before correctedreference/PUT in existingpipeline; no oracle tuning.
No endpoint keepalive completions outside cap. Report known usage/missingfooters.
Full84516130snapshot/workload unchanged. New run:
final/out/native_tool_agent_smoke2_20261110/.

Independentreview before launch: resume toolreceipt state, terminalstream,
missingtoolID and interruptedtoolattempt budget findings fixed with RED→GREEN
engineeringtests. Native request messages/tools schema and full responses logged
with endpoint/key excluded. Snapshot code/data/cohort/config before launch.
No task-specific patches or synthetic PUT changes. This is engineering smoke,
not proof bugfindinggain. Do not automatically enlarge benchmark after smoke.


Native smoke compatibility amendment before new requests: initial task55 request
and one diagnostic identical payload both HTTP400: tool_choice required needs
server --tool-call-parser. 2physicalbadrequests preserved,0tools;no task55retry.
Use native named testing_tool router (operation enum delegates actual4tools) so
vLLM can produce function calls without auto parser. NativeAPItool_calls retained
in history, nottextJSONfake. Test only task64 in new output native_tool_agent_named_smoke1_20261110,
max4newrequests/4tools, at most6requests including priorbadrequests across both
smokes, still <=original8requestcap;task55uses2/task64<=4. SamePUTs/budget,
no comparativeclaim. Cacheprotocolv2 marks changedwirepayload. Sourceoldkept.


## 2026-11-10 — User-authorized simple LLM discovery overnight full164

User yêu cầu thêmversionarm đơn giản,LLMdiscover missingcontrol/dataflow
criteria và concreteinputs, khôngHypothesis; dùng endpointthread vàlong-running
memory/schedule quađêm. Implement arm simple_discovery trong existingfinal code,
reuseCoverUp/SymPrompt feedbackidea và classicalDUcriteria;không tái hiện paper
engine. V9literalfeedback/V11DUfacts đã có; khôngclaimnovelty.

Scope fullfrozencohort164,157eligible/1454PUT,7shortfallskips;singlearm
20input/task,2LLMrounds→314logicalcalls,existingtransportretry3→942physicalcap.
ExactQwen3.5-27b-awq/4096completion/8192context/.7/seed314159/thinkingfalse.
2visiblePUT/task theoexistingorder, fullpublicbasecheck8s/PUT;40candidate–PUT
observations/task/1s, khôngsampler/solver. CorrectedHumanEval+reference và
8sconfirm_first_failures evaluation, per-taskfreeze trước independentoracle.
Producerpersist/freeze rồi isolatedCPUconsumer chạy chồnglấp, không nhận outcomes.

Newoutput final/out/simple_discovery_full164_qwen_20261110_164404, immutable
source/data/cohort/config, privateper-runroute ngoài repo; oldruns untouched.
Base/trace uses coverage.py+boundedASTcopy instrumentation for localbindingDU
and evaluatedatomicC3subset. StaticpairsMAY/feasibilityunknown; fullDU-paths,
heap/alias/interprocedural và listedunsupportedsyntax khôngclaimcoverage.
Baselinepartial/timeout khôngbiến emptyset thành fullcoverage:gainNone/pending.
Boundtarget phải thuộc đúngPUT, unboundLLMconcept giữhypothesis vàvalidinput.

TDD/regressions + independentreview trướclaunch;692tests pass/4skip gồm
24trace/armchecks, output/shortcircuittruthiness/coverageparity vàrealDUkills.
Reviewerfixes:baselineunknown propagation/freshCFmeasurement, crossPUTbinding,
nightquotaguardmissingwindowsfailclosed, metricNone trong runnerreport.

Detachedfullrun+Prefect1record/source/config/progress/results/report tiếngViệt.
Nightlysystemdtimer mỗi60min trong12h,≤3Codexresumes cùngexistingidlethread;
onlyv22/v69 accountpinned, samecurrentgpt6.1sol, requirefreshfiniteprimary+
secondary/modelbucket quota>10%; nếublockedmaxwindowreset/minaccount+300s và
GETrecheck trướcinference. Không fallbackaccountkhác, khôngduplicateactive
thread/run hoặcautomaticnewbenchmark. Endofrunreport rồistop.


## 2026-11-11 — Native agent smoke after user supplies parser-configured endpoint

User follows server-parser instructions and resupplies endpoint/model, authorizing
retry of operational smoke. New explicit run task64 only,4LLMrequests/4toolattempts,
4096completion/context8192/cap20inputs/10frozenPUT/native8s. Preserve prior failed
runs and4HTTP400 requests; this is a newly authorized post-server-change budget,
not hidden retry/resume/reset of unknown checkpoints. Same reviewed namednative
agent with error diagnostics. No other newbenchmark/fullrun. Report true outcome,
freeze/evaluation/replay and usage on new Prefect ID. Endpoint process/private
profile only. Outputnative_tool_agent_parser_ready_smoke1_20261111.

## 2026-11-11 — User explicitly authorizes full native-tool agent

User “chayj full di” after completed native smoke916da0e8. Launch full164,
157eligible/1454basepassPUT with exact smoke-passing immutable runtime,
not the earlier fixed5sampler controller. Native named testing_tool operations
sample/check/solve/submit, cap4physicalLLMrequests and4toolattempts per task,
failed calls count; max628ofeach over157eligible slots. Existingtrustedcompiler
supports110eligible tasks,47unsupported recorded without relaxingcontract;
7cohortskip slots. Runtime modelQwen3.5-27B-AWQ,4096completion/context8192,
20inputcap/task,10expectedPUT/task,confirmfirstfailures/native8s. No comparison
fairness claim, no new baseline or poolaudit. Sameprompt/toolbudgets as smoke.

One sequential agent producer (tool feedback within each task) overlaps one
CPUprocess evaluating finalized previous task. Persist agent transcript/tool
checkpoints + inputs before queue. Child reads cached inputs; no fresh inference
in evaluator. Per-taskfreeze precedesreference/PUT; no oracleoutcomes go back
toproducer. Source/config/cohort frozen beforelaunch, endpointprivateoutside
repo/Prefect. Prefect logs/progress/results/report continuously. Unsupported/
failed slots prevent falseCompleted; fullreceipt remains truthful partial.
Output final/out/native_tool_agent_full164_20261111/. No duplicate fullagent
job exists atpreflight; old84516130fixedsamplerfull isterminalFailed.

## 2026-11-11 — Data-flow candidate arm, trước authored smoke

Mục tiêu bản nhỏ là kiểm cơ chế, chưa kết luận PUT detection gain. Default criterion
`all_uses`; report sáu candidate projections với `pair_feasibility=unknown` và
`exact_adequacy=unknown`, kể cả ratio=1. Cartesian same-variable/scope inventory
chưa loại backward/killed/infeasible pairs. Mixed fallback dựa inventory;
definitions không candidate use vẫn trong denominator. BoolOp/Not predicates
unsupported tại guidance/projection layer, raw tracer không đổi; All-DU-paths
unsupported vì không đo ordered paths.

Một visible base-pass supported PUT đầu tiên theo packet order/task, source_limit=1,
target_limit=6; một full base suite sandbox trace, timeout tối đa 1s. Tối đa một
model completion/task, input budget theo shared settings; không seed, fuzz,
mutation, solver, concept metadata hoặc feedback. Giảm targets khi prompt quá dài,
không cắt source. Saved response được reuse khi restart; inputs freeze trước shared
reference oracle, sau đó chỉ reference-valid `arm_indices` được đo. Measurement
không feed về generation, không đổi oracle/scorer và không chứa expected outputs.

Authored smoke do root quản lý: ba functions, `gpt-6-luna`, reasoning `low`, tối đa
3 generation completions và 4 inputs/function (12 tổng), một Prefect run đã đăng ký.
Không gọi Qwen hoặc mở rộng benchmark; bug gain ngoài Plain/EP/BVA/DT vẫn pending.
CLI/API first release, chưa nối console allowlist/runner/source snapshot/budget
preview; không tạo console preset giả chạy được. Không thêm dependency/install.

### 2026-11-12 — Data-flow feedback(2), trước full run

Arm mới `data_flow_feedback`, giữ `data_flow` one-pass mặc định. Cùng source PUT
supported đầu tiên và full public baseline, tối đa 6 candidate DU targets; compound
predicate gate và unknown feasibility không đổi. Initial generation + tối đa 2
feedback rounds, tổng input slots/task chia divmod thành 7/7/6 khi budget=20.
Mỗi round chỉ nhận input objects; parser tolerant hiện có. Dedup canonical
args/kwargs; không fuzz, mutation, solver, regenerate seed hoặc dùng expected/output.
Feedback chỉ domain/status/exception class của original PUT, observed/new/missing
DU pair IDs, parse/duplicate rejections và already-tried calls. Giữ mọi unique
structurally valid input, kể cả domain-rejected, để reference admission độc lập.
Mỗi raw response/request checksum và native observation được persist trước round
sau. Native trace cap 1s; known wall timeout là unknown, lỗi infrastructure khác
propagate. Tối đa 3 logical calls/task, transport giữ recovery policy hiện có
(tối đa 3 physical attempts/logical call, kể cả restart). Không reset cap.
Tất cả rounds hoàn tất trước input freeze/reference; đo candidate coverage sau
reference chỉ trên accepted indices. Để giữ measurement độc lập và implementation
nhỏ, remeasure accepted inputs: tối đa 20 prefreeze +20 postreference native input
executions/source, ngoài full public baseline. Không claim exact adequacy hoặc
infeasible; All-DU-paths unsupported. Stop sớm khi không còn selected target gaps,
không có input slots hoặc context không đủ. Default one-pass và catalogue không đổi.

## 2026-11-12 — User tăng feedback budget và bỏ baseline comparison

User cấp phép Data-flow feedback2 full164 trên private route riêng:20inputs mỗi
round, tối đa3logical rounds =60input slots/task,≤348logical completions/
1044transport attempts cho116staticallysupported tasks,≤6960input slots.
Native trace≤6960prefreeze +6960post-reference source/input pairs. Run one-pass
đã chạy giữ20inputs/task và source snapshot cũ. Hai run chỉ generate/evaluate
arm tương ứng; không chạy Plain/EP/BVA/DT. Report chính standalone arm,
không yêu cầu baseline union. Feedback chỉ original PUT DU/domain/status,
không oracle outputs, giữ candidate feasibility unknown và All-DU-paths unsupported.

## 2026-11-12 — User-authorized Gemini DU diagnosis, bounded construction probe

Scope: saved Gemini134tasks (0–133) coverage, quality/feasibility of All-defs,
c-use,p-use,mixed,All-uses candidate objectives; All-DU-paths unsupported. User
asks long-run analysis and inputs outside full/naive, not resume cancelled runs.
Read-only baseline artifacts plus ≤19source comparisons, ≤100unique accepted
full-pool inputs/source and≤1900native data_flow traces (1s). Stop tracing a
source early if all Gemini new DU hits already witnessed in full pool.
One targeted HumanEval25 factorize source selected by missed loop objective
and code semantics before new model outputs:≤1logical/physical generation,
≤50inputs,4096completion/8192context. Prefer live Qwen route; only if dead,
Vertex gemini-3.1-flash-lite once, persistent exclusive
`final/out/.data_flow_vertex50_once.lock` checked/created before Vertex use;
never remove/reset lock to retry. No tool-fuzz/mutation seeds. Guidance names
remaining factor after small-prime divisions and trial-loop threshold; source
provided with contract and raw coverage, no hidden failure labels or expected
outputs. Freeze candidate inputs before reference/PUT check; no iterative tuning
from evaluation. New experiment max50inputs on1task, not full benchmark. Record
Prefect actual calls/tokens/source/output; missing data remains pending.

2026-11-12 diagnosis amendment: complete saved-full witnesses cover all55Gemini
new DU pairs after134native traces. One preselected factorize construction probe
received49input records (cap50), before any further model call;generation cap
now exhausted. Also compare the same preselected source's accepted full-pool
inputs against this probe's DU hits,≤100additional traces, still≤1900overall.
This is CPU measurement of saved inputs only, no new baseline generation or
model retry, no cancelled-run resume. Any novel DU witness is exploratory and
not a bug discovery claim; do not expand cohort based on probe evaluation.

## 2026-11-12 — User-authorized full Gemini Control-flow owner routing v2

User explicitly approved candidate routing/construction changes, requested Astra
plan first, root implementation then one full Gemini run. Plan:
research/concolic-concepts-2026-11-12/ASTRA_IMPLEMENTATION_PLAN.md.
Only control_flow, no fresh Plain/EP/BVA/DT/Data-flow/Simple or benchmark smoke.
Frozen existing cohort164slots/157eligible/1454base-passPUT;20inputs/task,
2rounds/<=314logicalgenerationcalls,3physicalattempts/logical(<=942),
Gemini gemini-3.1-flash-lite native Vertex,4096completion/18192context,
CFtrace1s/evaluation8s;64candidate-input–PUTobservations/task,6targets,
32Hypothesisdraws/concept/2seconds unchanged.

Treatment: owner-first routing per(input identity,PUT), target/concept round-robin,
unbound direct fallback with candidate/destination rotation, deferred pool and
unused quota carried to next round. Global pair dedup; provenance(round,id).
Predicate only soft ranking after direct opportunity, not trusted domain or hard
filter. Named correlated input guidance; existing descriptor backend unchanged.
Compact feedback reports duplicate/deferred/domain/miss counts and observed arcs,
no oracle outputs. Context fitting trims examples/static def-use/compact checks
before removing covered target context. No symbolic engine/solver/instrumentation
or source-edit alternative added; do not call this concolic reproduction.

Independent reviewer found metadata-type crash, unbound starvation and round2
context overflow. All reproduced RED before fixes; new regression tests added.
Existing default-BVA lazy import protected; authored C-native timeout fixture
uses0.2s instead0.01s so initialization does not race the intended hardwall check.
Full modular suite671PASS. No experiment/model/solver/PUT calls yet at amendment.
Future runtime/source/cohort hashes frozen in fresh output; persistent exclusive
Gemini run lock consumed before any Vertex operation. Per-task response persistence
and freeze before independent oracle/evaluation; isolated CPUconsumer overlaps
next task generation, outcomes never fed back. Report actual calls/tokens and
unknown attempts; missing metrics pending; Prefect same flow ID per source run.
Compare detection sets to saved Gemini CF35 and savedPlain+EP+DTunion92 only,
no new baseline workload. Selected-target hit rate is not whole-program coverage.
No gain or causal contribution of individual changes claimed before outcomes.

## 2026-11-12 — User-directed revert owner routing and real engine CF Gemini

User explicitly requests revert the just-tested owner-routing/prompt changes,
implement actual engine-derived path constraints and constrained bucket inputs,
then full Gemini again. Routing4files restored from before-edit copies and2new
routingfiles removed; previous outputs/checkpoints/reports retained. Astra plan:
research/concolic-concepts-2026-11-12/ASTRA_ENGINE_PLAN.md.

Treatment protocol crosshair-path-concepts-v1: original CrossHair0.0.112 with
Z3actual4.15.4 executes original PUT+fulltrustedcontract in bwrap. No author source
modification, source-edit mutant or own symbolic interpreter. Official explore_paths,
PushedModule/opcodehook; export path SMT before deep_realize, materialization SMT
and model separately. First engine witness must pass native trusted-domain,
target and ordered opcode-path equality before supplied to Gemini. Gemini concept
predicate conditions another actual engine search on the same path; native bucket
replay checks predicate/path/target before finalinput priority. Schema path_id is
optional for unsupported/direct fallback, not a fake symbolic proof.

Same164slots/157eligible/1454PUTfrozen cohort; onlycontrol_flow, no new baseline
or smoke benchmark.20inputs/task,2modelrounds/314logical/942physicalattemptcap,
6selectedtargets,64nativecandidate-input–PUTobservations incl engine replays.
Solver cap2seconds/target (1evidence+remainingconceptbucket),≤12s/task; bounds
integerabs1e6,sequence30,nested5 are search limits,notdomain. Per-job wall/setup
reported separately; UNKNOWN/unsupported/bounded no-witness never UNSAT/global
infeasibility. Initial type profiles from trusted prompt annotations or all saved
base examples; empty-untyped lists unsupported. Previous/baselinecall exclusions
keep literaltypes and owner scope. CrossHair symbolic-first, not DART seed tracing.

Native opcode observation runs originalsource once (line arcs checked against
coverage on authored short-circuit/loop/exception fixtures). Z3 helperthreads use
engine-onlyNPROC headroom; seccompdenies fork/vfork/processclone/exec; bwrap,
no network/hiddenhost,1GBAS/4MBfile/64FD and wallkill bounds remain. Dispatch
intents persist before native/solver; partial task restart fails closed rather
than silently resetting budgets. Completed-generation replay unchanged.

Independent review4mustfixes: persist dispatchbudget, bool/int exclusion, owner
scopedexclusion, bucketpriority+round/concept provenance; authored RED→GREEN tests.
672modulartestsPASS, originalengine9tests plus bucket/state/parity tests included.
Malformed direct concept_id metadata test reproduces mixedstr/intfreeze failure;
normalize nonstring metadata toNone, preserve canonical direct input and rawresponse.
No newbenchmark/model/solver workload outside authoredengineeringfixtures so far.

Gemini gemini-3.1-flash-lite native Vertex,4096completion/18192context,CFnative1s,
evaluation8s. Existing runner producer/isolatedCPUconsumer per-taskfreeze; persist
responses before buckettools; no oracle feedback. Freshoutput/immutable source
and environment manifest, persistent paidrunlock beforeVertex. One newPrefectflow,
config/progress/engine treatment/results/report artifacts; missing metrics pending.
Compare saved baseline CF35 and Plain+EP+DTunion92 only on matching evaluatedPUTs.
Report actualwrong/crash/resource perPUT, selectedtargethit vsfullcoverage distinction,
engine/bucket counts, solver/native units, modelcalls/known+unknowntokens. No claim
of novelty/coveragegain/buggain before outcomes. No automatic next run or capreset.
## 2026-11-12 — Full Control-flow typed construction, Qwen user endpoint

User yêu cầu thêm operations rồi ra lệnh chạy full bằng served model
`qwen3.5-27b-awq`. Một run mới, chỉ `control_flow`; không rerun/resume run cũ,
không baseline generation mới. 164 slots / 157 eligible tasks / 1454 base-pass
PUTs trên cohort hiện có; source/data/contracts/reference frozen riêng trước
inference, endpoint chỉ lưu private profile ngoài repo.

Protocol `control-flow-construction-v1`:15 typed operations, catalogue backend
CrossHair0.0.112/Z3 4.15.4. LLM trả construction ID + fields; parser/compiler cố
định giữ full contract/engine path. Z3linear chỉ int/bool, integer constants,
full path SMT + typed argument-symbol mapping. UNKNOWN/unsupported/search
exhaustion không infeasible; UNSAT scope gồm input exclusions. Native replay
kiểm domain/target/opcode path/predicate; concept semantics vẫn hypothesis.

Budget:20 final inputs/task,2rounds/task,max314 logical completions/942 physical
attempts;4096completiontokens/call,context8192 theo live advertised endpoint;
evaluation8s/input,CFnative≤1s/input,6targets/task,64nativeinput–PUTobservations,
2solver seconds/target(total≤12/task),≤1s trước LLM,phần còn lại sau construction.
Searchbounds |numeric|≤1e6,sequence≤30/nested≤5 là giới hạn search, không domain.
Giữ original retry/attempt policy, không reset khi lỗi hoặc mở run rescue.

Producer persist response và freeze từng task trước async CPU evaluation;
không đưa reference/PUT outcomes vào LLM feedback. Native jobs dùng sharedlock,
để existing frozen Gemini run chạy nguyên trạng. Record Prefect gồm config,
source/output, progress, treatment receipts, report và comparison saved-only.
Completed chỉ khi required evaluation/replay/source check hoàn tất; partial ghi
Failed thật, metric thiếu pending. Report tiếng Việt, denominator task/PUT/input
và call/token/unknown usage rõ; không đồng nhất target-hit với bug gain. Chờ
user quyết định run tiếp sau run được cho phép này.
## 2026-11-12 — Gemini smoke6: observed catalogue membership

User authorized Gemini after implementing actual catalogue measurement. Use
smallest proposed smoke scope, not a full benchmark: tasks0/5/18/81/99/120,
existing boundary_smoke cohort,1PUT/task; plain/ep_bva_v2/decision_table_v2,
20inputs/task/arm,4096completion/18192context,8seconds/input. Native Vertex
gemini-3.1-flash-lite;18logical generation calls/54transport attempts maximum.
No separate paid explanation/demo call, feedback loop, cohort expansion or
automatic followup. Freeze each task before reference/PUT evaluation; no outcome
feedback. Historical results/checkpoints remain unchanged.

Purpose: end-to-end catalogue accounting, schema/parse validity, observed
hit/miss/unknown/witnesses and disagreement with declared covers. Report unknown
and metadata failures separately; no semantic-grounding or comparative-efficacy
claim from smoke6. Report detection kinds and calls/tokens with denominators.
Independent reviewer ID-collision fix passed RED→GREEN;741modular tests pass.
Frozen source/config/cohort self-check passed. Output
`final/out/gemini_catalogue_smoke6_20261112_191746`; Prefect same-source record
`27809071-917e-4d75-be93-f2f317a1f773`,3artifacts API verified before workload.

## 2026-11-12 — Full164 Gemini sau catalogue smoke6

User explicitly requested "full cho gemini" after smoke6 completion. Run only
plain/ep_bva_v2/decision_table_v2 with byte-identical smoke runtime/prompts,
full HumanEval164 slots/157eligible tasks/1454base-pass PUTs.20inputs/task/arm,
4096completion18192context8s/input,target_programs10. Native Vertex model
gemini-3.1-flash-lite.471logical generation calls/1413transport-attempt cap;
1,929,216completion-token cap. Unknown attempts retain their original budgets.
No additional smoke, control-flow/data-flow arm or automatic followup.

Source-smoke: final/out/gemini_catalogue_smoke6_20261112_191746. New output:
final/out/gemini_catalogue_full164_20261112_193646. No responses/outcomes reused;
shared deterministic execution cache remains enabled. Per-task freeze before
reference/PUT, overlap evaluation with subsequent generation, no outcome feedback.
Record catalogue schema failures and observed hit/miss/unknown, keep valid inputs
when catalogue invalid. Missing predicates/selectors do not imply0%coverage;
semantic-grounding/base-coverage limits remain. Detection metrics separate input
counts, PUT counts and failure types. Report real config/progress/calls/tokens.

Same-source Prefect f4361b64-f059-4c5d-93d5-a9acf82bf57f with3artifacts APIverified
before workload. Existing smoke independent review/tests and frozen-source parity
checks apply; scope-adjusted runner self-check PASS. No production code changes.

## 2026-11-12 — Qwen full164 catalogue, user-supplied private route

User explicitly supplied an OpenAI-compatible endpoint and requested full Qwen.
Run only plain/ep_bva_v2/decision_table_v2;164slots157eligible1454PUT,
20inputs/task/arm,4096completiontokens/call,8s/input,target_programs10.
Qwen3.5-27b-awq advertised context8192 via GET/models; use8192 instead of
Gemini18192. Record this visibility/context difference, not a pure model effect.
471logical generation calls/1413transport-attempt cap; no extra benchmark/demo.
Keepalive uses existing scripts/ping_endpoint.sh,600s,accounted separately.

Reuse byte-identical completed Gemini catalogue runtime, with unchanged testing
prompts/measurement; no metadata-contract repair bundled into this run.
Missing predicates/selectors remain unknown; schema-invalid catalogue keeps
valid inputs. Full source retains generated responses and frozen inputs,
per-task freeze before reference/PUT,CPU evaluation overlaps next generation,
no outcome feedback. Shared native lock/cache; active control-flow endpoint is
different. No restart of other jobs or automatic followup.

Output final/out/qwen_catalogue_full164_20261112_232556. Endpoint file remains
private outside repo; do not publish URL/keys in logs/Prefect/memory.
Frozen source/config/cohort self-check PASS; source Gemini catalogue runtime
already had741engineering tests and independent review. No production changes.

## 2026-11-13 — VF3 watched smoke3 → conditional full Qwen

User yêu cầu JSON Schema client-only, tối đa1enforce/coverage feedback round cho
EP/BVA và DT, đặtvf3, hủy run cũ rồi watched smoke trước full. Old Qwen
0086fa3b Cancelled,11responses/12attempts preserved. Không resume old source.

Smoke: tasks0/5/18 trong boundary_smoke,1PUT/task,plain/ep_bva_vf3/
decision_table_vf3;3tasks3PUT,20retained inputs/task/arm,4096completion8192context,
8s/input. Plain1call;VF3 tối đa2calls/task/arm,15logical/45transportattempt cap.
Structured response_format enforced; missing/invalid metadata+uncovered target
feedback cached. No PUT/oracle outcomes before freeze. Initial10inputs, retained
old inputs then new inputs within20; no target deletion or valid-definition drift.

Output final/out/qwen_vf3_smoke3_20261112_235235; Prefectc962cd86-fb53-45b3-8d31-
3e99fa3a6dd2. Independent reviewer found/fixed usage-prefix overlap,
target-definition drift and uncached feedback resume. Full regression before
launch; no notebook/dependency changes or paper reimplementation.

Gate for full: all3slots generation/evaluation/replay complete, no transport or
schema errors, structured format present, bothvf3 arms exercise feedback repair
or supplementation and preserve<=20inputs, membership-ready catalogue and useful
observed coverage (unknown reasons explicit, no all-prose result likev2).
Bug gain not required. Fail gate→fix within authorized smoke scope without
expanding cohort; preserve failures/call budgets and report amendments.

Full conditional authorized:164slots157eligible1454PUT,same3arms/settings,
runtime byte-identical passing smoke,785logical/2355transportattempt cap.
Full has its own Prefect/output, no extra arm or subsequent automatic run.

### 2026-11-13 — VF3 smoke amendment trước corrected smoke

First watched task0 produced4responses (Plain1,EP1,DT2), then stopped before
task5:EP feedback skipped due context overflow;DT original actions omitted,
repair changed IDs. StateFailed/treatment gate, evaluation pending, no gain claim;
Prefectc962cd86/source qwen_vf3_smoke3_20261112_235235 preserved.

Root fixes before corrected smoke: compact feedback sends spec/contract plus
required catalogue fields instead of full PUT/common packet; no truncation of
spec/contract. EP generation schema onlyid/description/predicate;DT original
actions required;BVA transform required. VF3 guidance removes unrelated long
soft example, stresses executable quantifiers/actualnames and concrete DT rules.
No task-ID logic or hidden outcome tuning. Same tasks0/5/18,inputs/budgets;
corrected smoke max15calls, diagnostic4 separate (combined maximum19logical
calls across these attempts). No full until corrected treatment gate passes.

Corrected source final/out/qwen_vf3_smoke3_20261113_000100,
Prefectb6afaa54-cfed-4526-95a9-019e7946e45e with3artifacts verified prelaunch.


## Amendment 2026-11-13 — structural và semantic obligation arms

User yêu cầu giữ CF hiện tại và thêm `spec_obligation`, `control_flow_obligation`; không retrieval hoặc concolic. Combined chọn cả C1/C2 gaps lẫn semantic miss/unknown, không dừng khi code đã phủ. Spec-only không dùng structural targets làm generation objectives. Cả hai nhận source-bound CFG/static DFG và cùng fixed soft examples (dedup/early return/overwrite với correct-use counterexamples).

Limits: tối đa2logicalcalls/task/arm,20selectedinputs/task/arm,3semanticinstances,6structuraltargets,32Hypothesisdraws/instance/2s,64candidate–PUTobservations/task và300basereplays/task; native trace tối đa1s. Existing transport attempts và shared oracle/scorer không đổi. Program IDs/hash/original line/arc được bind; predicate + reach chỉ chứng nhận scenario membership, applicability/propagation chưa là proof.

Treatment checks trước efficacy: parse complete direct inputs dù metadata lỗi; Hypothesis unsupported ghi đúng receipt; dedup full recorded base, không chỉ prompt-visible; partial trace không biến unknown thành miss; witness cache giữ kết quả qua lần report; freeze barrier/replay và JSON-stable config phải pass. Independent reviewer đã chỉ ra bốn gaps trên và đã có regression fixes. Không dùng task-ID bypass, hidden outcomes hoặc oracle feedback cho producer.

Primary efficacy còn pending: incremental PUT detections ngoài Plain/EP/BVA/DT trên cùng evaluated cohort/scorer; phân biệt input yield, scenario hit, PUT detections và extra union. Soft examples/Hypothesis không được claim có lợi chỉ từ parse success/coverage; cần provenance của direct vs sampled và overlap. Engineering authored fixtures không là benchmark evidence. Phiên này chưa launch model/benchmark/evaluation run; user quyết định lần chạy và scope/budget riêng.
### 2026-11-13 — VF3 single-original-table correction

Second task0diagnostic5responses:EP metadata-ready and feedback improved observed
class hits6/10→10/10,18inputs;boundary-definition changes rejected. DT failed
merge/original consistency;stop before next tasks,noevaluation. Source
qwen_vf3_smoke3_20261113_000100/Prefectb6afaa54Failed preserved.

Correct DT generation: model returns one original table in catalogue.rules,
concrete boolean combinations/status/actions and condition_predicates. Code
derives legacy original_rules and feasible unmerged rules without altering
conditions/actions; no independent merged table for model to contradict.
DT guidance asks specification actions rather than algorithm/fault rows.
No task-ID tuning or outcome access.52focused schema/VF3/transport testsPASS.

Continuation smoke source qwen_vf3_smoke3_20261113_001236,
Prefect5e9f8016-0e48-4249-8f97-768f51fc865d. Reuse received Plain+EP task0 calls
and EP generation/feedback from prior diagnostic, explicitly linked in config;
no repeat for these3responses. NewDTtask0 and tasks5/18 max12newlogicalcalls,
15representedcalls in finalsmoke;combined diagnostic+continuation max21unique
logicalcalls. Same3tasks/3arms/budgets,nofulluntilgate.

### 2026-11-13 — Typed argument and fixed Boolean-row schema amendment

Watched task5found unconstrained JsonValue→giantinteger/truncated response,
misspelled nominal/context keys,and duplicate DT combinations. Stop third source
qwen_vf3_smoke3_20261113_001236 beforetask18;10represented responses(3reused),
7newcalls;task0evaluationcomplete,task5pending. Prefect5e9f8016Failed;preserveall.

Before next smoke: typed argument schema from source annotations,int±2^32,
lists<=30,strings<=1000;context/nominal schemas use actual parameter names.
Raw JSON values preserved after type validation(no int→float coercion).
DT schema chooses1–4conditionsC1..Cn and fixes every Boolean combination row
Rbits exactlyonce;LLM supplies predicates/actions/feasibility/reasons/inputs.
Code reconstructs conditions and legacy views;no duplicate/combinatoric omission
possible within chosen condition count. This is bounded DT,not proofspeccomplete.
No model-derived redundant exclusions override the original table.

Next source qwen_vf3_smoke3_20261113_003236,
Prefect818efb15-b6a7-428c-8200-de77081a08ee. Reuse6responses(task0allarms+Plain5),
newcallsmax9 forVF3task5andalltask18,15representedtotal. Task0DT primary table
normalized from saved feedback by dropping contradictory redundant exclusions;
predicates/Boolean assignments/actions/inputcalls unchanged. Explicit lineage in
configandgeneration.normalization_source. No repeat LLM/native calls for this
normalization.57focusedtestsPASS before final context/row regression addition.
Combined diagnostic+finalsmoke max25unique logicalcalls, same3tasks/noexpansion.
Full remains conditional on actual schema/feedback/measurement gate.

### 2026-11-13 — VF3 smoke gate passed, full launch

Final watched smoke818efb15 completed3/3tasks/3PUT,0generation/evaluation errors,
3/3sourcechecks/read-onlyreplaysPASS.6/6VF3task-armcataloguesmetadata-ready;
observed EP36/36classes hit,BVA3/10boundariesfullyhit(7miss),DT9/11declared
feasibleoriginalruleshit(2miss),0unknown. Feedback exercisedEP3/3andDT2/3;
DTtask5earlystopped. Actualdetection0/3allarms,notan efficacy gainclaim.
14representedresponses/0unknown,6reusedlinkedresponses/8newcalls;31780represented
tokens,18150newtokens. Combineddiagnostic+finalsource24newmodelcalls;no additional
cohort or hidden outcome tuning. All failed source snapshots/checkpoints retained.

Before full, offline hardening preserved numericbool subclass inputs and converted
canonical metadata literal failures into feedback errors instead of taskcrash.
59focusedtests and782modularsuite testsPASS(3existingSDKwarnings). Two-file
validated runtime amendment recorded inSMOKE_GATE.json;no native/model rerun for
publishing gate. Fullclones validatedruntimebyteexact,notworktreefutureedits.

Authorized full output qwen_vf3_full164_20261113_004516:plain/ep_bva_vf3/
decision_table_vf3,164slots157eligible1454PUT,20inputs/arm4096completion8192context
8s/input,target10;785logical/2355transportattempt cap,3215360logicalcompletion
token cap(excludes unknown transport attempts/keepalive). Newfullresponses only,
no smokegenerationreuse inbenchmark. Per-taskfreeze/evaluationoverlap,nooutcome
feedback. DTVF3bounded1–4conditions andall2^nrows;semanticgrounding remainspending.
No other arm or postfullautomaticfollowup.

## 2026-11-13 — Resume VF3 sau30phút, new private endpoint

User supplied replacement Qwen3.5-27b-awq endpoint,then explicitly confirmed
"Bắt đầu sau30phút". Not-before2026-11-13T06:35:20UTC/13:35:20VN,anchored at
original instruction time06:05:20UTC. No model/native workload before deadline.
Continuation only37unfinishedeligible tasks/335PUT from859642cbFailed;
same Plain/EPvf3/DTvf3,20inputs4096completion8192context8s,target10.
Keep cumulative785logical/2355transport caps;remaining task call cap185 includes
cached task122calls,so actual new completions may be lower. No expandedcohort.

New source qwen_vf3_resume37_20261113_131222,Prefectaef89551-c329-4f15-88d9-
5977609a286c. Runtime pinned to original read-only frozen runtime;127completed/
skipped task slots inherited through read-only paths,only37missingtask directories
copied writable. Task122alreadyhas2receivedresponses+1unknown archivedattempt;
all574responses/576attemptrecords imported,per-call retry budgets notreset.
No regenerated old response or repeated completed evaluation.

Offline checksPASS:sourcehashes/all37taskmanifests,initialprogress574received/
576attempts/0newcalls,127completed-or-skippedslots1119evaluatedPUT. Newprivate
route kept outside repo/no URL or keys in artifacts. Sourcefailedrecord unchanged;
newrecord explicitlylinks sourceflow/run. Controller checks deadline and Prefect
cancellation before modelconstruction. No autoadditionalrun after continuation.


### Amendment 2026-11-13 — sửa tích hợp Pynguin và khôi phục Gemini (user authorized)

User: “ok, làm hết đi, xong chạy lại với gemini”. Source run
`pynguin_hybrid_gemini_json_20261113_205618`, Prefect
`3b79a986-4d63-411f-be80-57acd94f9273`, terminal Failed. Chỉ xử lý60 task
lỗi generation; giữ nguyên104 task records đã evaluation/skip, packets, received
responses và retry history. Không dùng efficacy outcomes để chọn/tune input;
selection dựa trên generation failures đã ghi.

Sửa adapter: thay compiler subset bằng shared trusted-contract validator trong
bwrap, trước freeze và không oracle/PUT outputs. Missing/invalid contract không
được mặc định valid. Validation owner lỗi thì từ chối owner đó; giữ input hợp lệ
của owner khác dạng partial. Extraction chỉ mở rộng cho sequence được AST chứng
minh độc lập và immutable module constants; prior results/mutable state vẫn reject.

Tách lỗi từng arm: Gemini độc lập không bị Pynguin chặn; guided thiếu evidence
được unavailable. Unsupported owner CFG analysis chỉ làm gap unknown, không làm
mất seeds hợp lệ. Unavailable không thành0 detections; arm-specific denominator,
union/gain chỉ trên task có đủ3arms. Kết quả kế thừa và khôi phục ghi protocol
riêng, không claim một full rerun đồng nhất.

Model/settings/cohort/visibility không đổi: gemini-3.1-flash-lite Vertex,
HumanEval164slots/157eligible/1454PUT;20inputs/task/arm,4096completion/context8192,
native8s,Pynguin10ssearch/30swall/200soft executions/64captures/ownerlimit10.
47 task chưa có owner search được search trong budget gốc.13 task đã có owner
receipts chỉ tái extraction test artifacts trong sandbox (≤30s/owner), không
redispatch search hoặc reset failed-owner attempts. Giữ2responses task141;
≤238 logical calls mới,≤714 transport attempts mới, vẫn≤628logical/1886physical
cumulative cap. Bốn unknown attempts lịch sử và364responses source giữ nguyên.

Run mới có immutable source/config, source receipt hashes, một Prefect record và
observer chỉ đọc artifact. Report Việt ngữ ghi actual/inherited/new costs,
unavailable/failure/skip và mẫu số. Chỉ Completed khi đủ evaluation/replay và
không còn arm unavailable; không tự chain run hay mở rộng dataset/budget.
## 2026-11-14 — Resume VF3 DT bỏ cap sau30phút, source cbee7d83

User cho phép resume bằng private endpoint mới, served model qwen3.5-27b-awq,
không bắt đầu workload trước06:51:31UTC/13:51:31VN ngày14/11/2026
(30phút từ06:21:31UTC). Source cbee7d83 Failed preflight ContextTooSmall,
0newresponses/attempts; continuation mới chỉ140eligible task/1294PUT còn thiếu.
Giữ85responses/226attempts/141unknown và24completed/skipped task slots,
frozen runtime byte-identical, context12288/completion4096/native8s,
Plain20/VF3initial20+feedback10, cumulative785logical/2355transportcaps.
Không reset retry history, không regenerate received responses hoặc chạy completed
tasks. Endpoint private ngoài repo; preflight tại deadline, capacity chưa xác nhận,
không tự hạ context. Observer cập nhật cùng một flow ID của output mới; chỉ
Completed sau evaluation/replay/source checks. Không tự nối run khác.



## 2026-11-14 — User-authorized Gemini CF original/v1/validated comparison

User cho phép plan+implementation rồi full Gemini so original CF, obligation vừa
rồi và validated version; union không Plain. Plan:
`docs/plans/2026-11-14-scenario-validation-gemini.md`. Đây là amendment trước
fresh generation/outcomes của comparison mới; old results đã dùng để diagnosis,
không coi cohort là unseen. Không hardcode task-specific rules/input witnesses.

Ba immutable runtimes: original CF từ Gemini full4 snapshot12/11, obligation_v1
final snapshot63511061 (parser fixes uniform; không tái hiện mixed old losses),
validated_v2 từ source sau verification/review. Cùng Gemini3.1FlashLite/Vertex,
164slots/157eligible/1454PUT,20inputs/task/variant,4096completion18192context,
seeds314159/271828,temp0.7,8s native,confirm_first_failures. Tối đa314logical và
942physical attempts/variant; total942logical/2826physical/9420input slots.
Không thêm paid smoke/control arms ngoài ba variants, không regenerate cohort.

Operational scenario witnesses dùng bounded primitive local state/ordered events,
không proof requirement/bug. Unknown cho unsupported/missing/partial evidence;
input predicate+line reach legacy không đủ nâng thành new semantic hit. Original
source không transform; no reference/oracle feedback trong generation. Giữ cả
C1/C2 targets và scenarios trên covered code. Native generation caps nhưv1.

Reuse per-task freeze + independent reference/PUT confirmation + read-only replay,
shared native lock và existing execution cache. Ba variants generation mới, không
import old responses. EP+BVA v2+DT v2 Gemini baseline saved union79PUT chỉ đọc;
loại Plain khỏi mọi workload/union. Report allsingle/pair/cumulative/allunion,
gained/lost/shared, unique inputs, wrong-value/crash/resource, calls/tokens và
unknown attempts; applicability không đồng nhất scenario hit. Partial source
không Complete và metric thiếu pending; không tự restart fresh fullrun.

Independent review đã phát hiện/fix stale multiline-after state, decorated/nested
scope, unsupported generator return và helper-name shadowing; authored regressions
đi kèm.1003engineeringtests pass/5skip/8dependency warnings trước snapshot.


## 2026-11-14 — VF3 explicit endpoint404 recovery, user yêu cầu thử lại ngay

Source d26f9a37 Failed chỉ do stored permanent404guard, không có completion mới;
private endpoint preflightPASSmodelqwen3.5-27b-awq/context12288. User cung cấp
notebook readiness và yêu cầu thử lại. Continuation mới chỉ140missingtasks/1294PUT,
reuse24completed/skippedslots và85receivedresponses. Trước workload, archive140
active failedcompletionHTTP404attempts bằng existingarchive_failed_attempt helper;
chỉ sửa output mới, không sửa oldattemptbytes hoặc globalpermanentfailureguard.
141unknown/226attemptrecords giữ nguyên;task17initial còn1/3attempt,139taskkhác
còn2/3attempt. Cumulative785logical/2355transportcaps,context12288/output4096,
Plain20/VF3max30/native8s và pinnedruntime/runner giữ nguyên. Offline transport
checksPASS:guard reproduced,explicitarchive dispatchattempt2/3,response reuse,
cap3 enforced,0network. Không regenerate receivedresponses hoặc resetbudget.
Output mới cóENDPOINT_404_RECOVERY.json, source/callhashproof, config/progress/report
và mộtPrefectflowID. ConcurrentGemini run dùng endpoint độc lập; native sharedlock
giữ nguyên. Không sửa notebook, không tự chain run khác.

## 2026-11-14 — User cho phép hoàn tất Gemini scenario comparison

Continuation của bab20457, chỉ missing slots. Giữ641received responses và25unknown
attempts; source matrix/checkpoints byte-identical. Inherited completed/skipped
slots:original82,v1163,v2160. Task82/95reuse saved serialized inputs, không gọi
lại model. Bỏ derived Hypothesis cache khỏi source hash guard trong output mới;
không bỏ code/data checks. Shared InputGenerationStage dùng persisted JSON view
trước freeze để tránh mixed str/int metadata keys; args/kwargs strings giữ nguyên.

User nói “cho chạy nốt đi”: cấp thêm3attempts cho đúng4requests429đãexhausted
(22propose,24construct,29propose,34construct), request_id bound, max6total/request,
backoff60s khi retrygrant. Default3attempts/call khác giữ nguyên. Physicalcap tổng
2826→2838(+12); logical942/input slots9420/domain/timeout/scorer không đổi.
Received requests/responses không regenerate, unknown history không reset.
Completed receipts trỏ về source leaf đã verified; chỉ missing leaf metadata được
rebuild cho runtime paths mới. Final report includes inherited/new usage và phải
verify source/imported response/input hashes trướcCompleted.0Plain.

### Amendment2026-11-14 — full3arm Qwen user authorized

User cung cấp OpenAI-compatible endpoint và model qwen3.5-27b-awq, yêu cầu
“chạy cho cái này đi, full3arm kia”. Run mới full164/157eligible/1454PUT:
Pynguin + independent EP/BVA VF4 + Pynguin-guided VF4; không thêm Plain/DT/CF.
Giữ reviewed Gemini recovery implementation,20inputs/task/arm,4096completion,
8192context,native8s,628logical/1884physical attempt caps. New full generation,
không reuse Gemini inputs/searches/responses/outcomes. Pynguin10ssearch/30swall/
200soft executions/64captures/ownerlimit10 như cũ. Full-contract sandbox validator
chỉ ở adapter Pynguin;VF4 compile_domain subset giữ nguyên,unknown_inputs báo riêng.

Endpoint/model readinessGET verified served name/context≥8192. Private endpoint
profile ngoài repo, không URL trong config/Prefect/memory. New source snapshot,
one run record/observer; unavailable pending riêng, union/gain trên đủ3arms,
per-taskfreeze trước oracle/PUT. No ongoing watch/autofollowup sau launch.

## 2026-11-14 — User-authorized Qwen rerun original CF vs retained obligation v1

User xác nhận Gemini rồi yêu cầu chạy lại trên endpoint Qwen mới; served model
qwen3.5-27b-awq, advertised max context12288. Chỉ2variants original_cf và
obligation_v1; validatedv2 đã retired, không sinh Plain hoặc baseline EP/DT mới.
Original algorithm/prompts clone frozen Gemini-original CF;v1 từ commitdc638379.
Shared transport overlays và JSONfreeze fix được hash-record, không sửa algorithms.

Full164slots/157eligible/1454PUT,20inputs/task/arm,4096completion/12288context,
8s native,confirm_first_failures,seeds314159/271828,temp0.7;628logical và1884physical
attempt cap,6280input slots. Fresh generation, không import received calls.
Context12288 khác Gemini18192 và oldQwenbaseline8192; report không claim isolated
cross-model comparison. Tokenizer404fallback là estimate, không exact upper bound.

Union baseline saved Qwen EP+BVA v2+DT v2 source7557c4df,113PUT; cùng frozen
cohort/reference identity, không Plain, không trộn Gemini baseline79. Final
report single/pair/allunion,gained/lost/shared,wrong-value/exception/resource,
unique valid inputs và known/unknown cost. Per-task freeze trước oracle,
producer không đọc outcomes; shared native lock và read-only replay.

Private routing snapshots ngoài repo/Prefect, không endpoint/key trong artifacts.
No cache directories trong sourceguard; staged source data hashes và2runner
self-checks PASS. Independent review không blocker, baseline157task/1454PUT/
union113/inputfreeze/referenceproofPASS;no model/benchmark trong engineeringchecks.
User yêu cầu chạy lần này; không tự nối thêm run hoặc hồi sinhv2.

### Amendment2026-11-15 — Qwen endpoint restored, resume39 HTTP404 tasks

User explicitly: “CHECK ENDPOINT LAI ROI CHAY LAI”. GET models + tokenizer
readiness passed exactqwen3.5-27b-awq/context12288(server), configured8192 unchanged.
New continuation selects39tasks with saved model arm failures HTTP404, inherits
125task records. Reuse all Pynguin batches/searches and packets; never repeat
native search. Keep378receivedresponses and448attempt records incl70unknown.
Archive69canonicalfailed404request directories byte-identical in NEW output so
checkpoint can spend remaining original3attempt cap; do not increase/reset caps.
No successful response regeneration. Frozen runtime identical source; scope
threearms164slots157eligible1454PUT20inputs4096completion/native8s unchanged.
Global628logical/1884physical cap remains; remaining≤250responses/1436attempts
upper bound (actual finite slots smaller). One Prefect record/new output links
source; sourceFailed unchanged. No ongoing watch/autofollowup.

## 2026-11-15 — User-authorized Qwen endpoint-restored continuation

User xác nhận endpoint sống và yêu cầu sửa adapter rồi chạy tiếp. Source
2c8be417-2795-4402-a863-fc7c55c909a0 được giữ nguyên; new output
final/out/qwen_cf_v1_recovery_20261115. Giữ393responses tổng (CF140/v1253),19unknown
attempts, CF164completed/skipped receipts. V1reuse146saved input batches gồm139
eligible+7skip; chỉ18taskthiếu được sinh thêm. Không chạy lại CF hoặc baseline.

Caller guard optional validate_generation khi interface có method; mandatory
validate_generated_inputs và freeze vẫn giữ. Algorithm/prompt/data/scorer/budget
không đổi, snapshot code cũ giữ, không lấy dataset/source user đã sửa trongworkspace.
Chỉv1checkpoint overlay request-bound replay policy:18stored404requests được retry
sau endpoint restored, max3attempts tổng/request, cũ1hoặc2vẫn tính; không tăng cap
1884physical/628logical, không reset history. New404 vẫn dừng ngay,401không override.
Per-run private routing snapshot mới,GET/models confirms đúngQwen27B/context12288.

35transportchecksPASS,independentreview không codeblocker. Hai runtime selfchecks
PASS; actual snapshot runner cachedgenerate task0 PASS vàfreeze recovered,
253responses giữ nguyên,0model/native/oracle workload trong check này. All received
response/input hashes imported; final verifies oldsource/import hashes beforeComplete.
Prefect record mới source-linked, chỉCompleted khi v1đủevaluation/replay và union
khôngPlain xong. Không tự mở rộng hoặc hồi sinhvalidatedv2.

## 2026-11-15 — User-authorized finish only Qwen154/155/158

User yêu cầu chạy đúng3taskfailed, không fullrerun. Sourcee4e4db69 giữ nguyên;
newoutput final/out/qwen_cf_v1_finish3_20261115,inherit419responses/19unknown,
CF164slots vàv1161slots đãverified giữ nguyên, chỉ28PUT/3taskchưa evaluation.

Lỗi resume cũ: dùng prompt dựng lại để so với request-bound grant cũ. New
explicit frozen-request replay directive được hash/request-ID approve theo call;
messages trả nguyên savedmessages trước tokenization khi directive hợp lệ. Validate
params temperature/max_tokens/seed,phase/spec/contract/signature/inputbudget và
sourcehash/numberedcode. Không nới checkpointguard, không sửa prompts fresh,
SOFT_EXAMPLES/INSTRUCTION literals giữ nguyên. Source requests và responsehistory
được giữ;18grantfiles lịch sử vẫn lưu nhưng chỉ3pending requests được chạy.
Default3attempts tổng/request/caps628logical1884physical không đổi; noPlain/noV2.

Actual frozen Evidence+messages checks154/155/158 PASS exactoriginalrequestdigest,
0tokenizer/model/native calls.57transport/spec tests PASS;independentreviewclear,
prepared source/control hashes và2runner selfchecksPASS. Freshconstruct phase nếu
cần vẫn dùngv1bình thường, tối đa2logicalcalls/task nhưsourceconfig.

Endpoint hiệnHTTP404ởGET/models: worker sẽchờpreflight30s/poll tốiđa6giờ trước
completion; chỉ bắt đầu đúngmodel/context. No attempt consumed whilewaiting.
CF inheritedcomplete đượcskipkhông worker/model call; v1completed161receipts skip.
Phải freeze rồi independentreference/PUT/replay cho3task, finalunion with saved
QwenEPDT113/noPlain vàverify source/import hashes trướcComplete. Không tựrerun
benchmark hoặc gọibaselinegeneration; parentrecord chỉCompleted khi fullrequired
evaluation vàcomparison đủ. Source/data user sửa ngoài snapshot không được đưa vào.

### Amendment2026-11-15 — guided frozen packet repair, complete24arms

User yêu cầu “thế m làm gì cho đủ đi” sau resume24guidedfailures Artifactchanged.
Rootcause offline task139:conservative tokenizer khi endpoint404 cắt9coverageowner
rows xuống8(1130→1016estimated tokens),remote tokenizer restored cắt khác; việc
rebuild informed_packet làm guard immutable từ chối trước completion. Fix reuse
exact frozen informed_packet after verifying common public packet, owner sources,
seed/coverage/gap evidence and reachable trim; retain context fit check. Không
bỏ provenance guard hoặc đổi request identity/seed/prompt giữa retry attempts.

Continuation only24guidedfailedtasks;inherit140taskrecords,copy42successful
responses/90attempts(48unknown) thuộc24task. Keep456responses/526attempts cumulative
source history including70unknown, cap628logical1884physical unchanged.
Pynguin+independent generated inputs giữ nguyên;0search/reextract/newindependent
calls. ≤48newlogicalguidedcalls; ≤120newtransportattempts from remaining original
3cap(guided initial1historicattempt/task→2remaining;feedbacknew≤3/task). Same
20inputs4096completion8192context8snative and per-taskfreeze. New output/runtime
only generator fix overlaid;source output unchanged. Prefectsame-source linkage,
armavailability truthful;remaining unsupportedPynguin not silently promoted.

## 2026-11-15 — User-authorized CF cũ mở rộng spec và native feedback

User clarifies mở rộng từCFcũ, rồi explicitly yêu cầu chạy full trênQwen endpoint
hiện tại. Newprotocolcoverage-concept-spec-feedback-v1: round0concepts+seedinputs
+optionalobligations→Hypothesis/native observation→round1feedbackrepair. Giữ2calls,
C1/C2targets,sourcebinding,fullbase dedup,nativegate,freeze/oracle. Spec scenarios
bổ sung trêncoveredcode, metadataerror/broadbasehit không bỏ vòng sửa cuối.
32native observations reservedround0,64total;interleave direct/concept/obligation
queues. ≤6concepts+3obligations/round,32draws/2s mỗiinstance;20finalinputs.
Noarbitrarycode/checker-v2/retrieval/concolicprerequisite, noexpectedoutputfeedback.

Chỉnewcoverage_spec_feedbackvariant chạy164slots/157eligible/1454PUT,20inputs,
4096completion12288context,temp0.7,seeds314159/271828,native8s,
confirm_first_failures,Qwen3.5-27b-awq. Freshcap314logical/942physical/3140inputslots.
CFgốc39PUT,V1cũ53PUTvàEP/BVA+DT113PUT dùngsavedresults;không chạycontrolgeneration,
khôngPlain/retiredvalidatedv2. Comparative unionallsets,gained/lost/shared,
wrong-value/exception/resource vàusage theoactualsource/runconfig.

Runtime clone từcompletedQwenv1strictsnapshot, overlay chỉ3files:
arms/coverage_feedback.py,control_flow/feedback_prompts.py,arms/spec_obligation.py.
Giữ nguyênfrozen dataset/spec/contracts/referenceprovider/evaluator; không đưa
concurrentworkspace edits vào benchmark. Algorithm mới được hashreceipt rõ;
oldoutputs/checkpoints/source untouched, parentverifiesoldsourceinventorybeforeComplete.
Per-taskfreeze/native lock/isolatedCPUconsumer vàsource+replayverification reused.

115focusedengineeringchecksPASS +3authoredsnapshotpipeline/replaychecksPASS.
Independentreviewclearonimplementationandlaunch;snapshotselfcheck/sourcehashesPASS.
Fullworkspacecheck còn12unrelatedfailuresmissinghistoricalfixtures/cohorts và
concurrentreference/BVAbehaviorchanges, không sửa cácchỗ đó để che failures.
EndpointGET/modelsPASSQwen27B12288,privateprofileoutsideartifacts,secretsnotprinted.
Runbackground;observerindexsameflowID,Completeonlyfullrequired eval/replay/union;
không tự mở rộng/rerun hoặc agentwatchcontinuously.

## 2026-11-15 — User replacement endpoint for CF feedback+spec continuation

User cung cấp route mới saungrokERR725bandwidthfailure, tiếp tục authorizedfullrun.
Newoutput final/out/qwen_cf_spec_feedback_resume_20261115 từb73f5ae8sourcefailed;
140missing taskslots, giữ24completed/skippedslots gồm17eligible160PUT;35received
responses,1unknowntransporthistory giữ nguyên. CF39/V153+EPDT113savedcontrols giữ,
khôngmodel/nativecalls lại cho completedcontrols. NoPlain/noValidatedV2.

Sameprotocol/caps314logical942physical/20selectedinputs4096completion12288context,
8snative,seeds314159/271828,temp0.7,32first/64totalnativechecks;6concepts+3obligations
perround,32draws2s. Algorithm/data/spec/contracts/reference/evaluator frozen source
không đổi, không đưa concurrentworkspace edits vào. Onlyfeedback_prompts.py thêm
explicit saved-request replayhelper cho approved pending call17round0 trước
retokenization,source/settings/digestcheck;freshdefaultpromptbody unchanged.
No capincrease/reset hoặc bỏ unknownattempt. Sourcehashes/inheritedinputs/imported
responses phải verify trướcCompleted,sharednative lock/per-taskfreeze/read-onlyreplay.

NewrouteGET/models đúngQwen27B12288 và actualtransport tokenizerremotecountPASS,
0completionprobe. Private per-run profilesoutsideartifacts.72authoredtransport/spec/
CFfeedbacktestsPASS;actualsavedrequest17round0proofPASS,2controlstatescomplete,
snapshotselfcheckPASS,independentreviewclear. Historicalfailedsource preserved.
Runbackgroundobserver cùng1flowID source-linked;khôngautorunnewbenchmarkafterfinish.


### 2026-11-15 — Chia continuation CF + spec/native feedback theo yêu cầu user

Giữ47 terminal task receipts;117 task còn lại chia disjoint59/58 cho hai private endpoint cùng Qwen3.5-27B-AWQ. Task41 đã frozen giữ inputs và hai received calls; không reset attempt history hoặc tăng2calls/20inputs mỗi task. Giữ nguyên immutable runtime/spec/contracts/reference/evaluator, context12288/completion4096/native8s và shared native lock. Source88cf018d bàn giao Cancelled; mỗi shard có record Prefect riêng. Merge read-only sau hai shard evaluation/replay đủ scope, kiểm164receipts/1454PUT rồi so saved CF39/V153/EPDT113, không Plain và không gọi lại controls. Independent review đã clear sau sửa frozen-module imports và source pointer artifact.


### 2026-11-15 — Bổ sung endpoint thứ ba, chia lại phần còn lại

User yêu cầu ba endpoint cho ba run song song. Sau khi drain task64/66, giữ70terminalreceipts;94task còn lại chia disjoint32/31/31. Hai task64/66 có frozen inputs và4receivedresponses được nhập lại nguyên bytes, không gọi model lại. Hai record shard cũ Cancelled vì bàn giao; handoff là read-only view, không tạo experiment giả. Mỗi run mới có Prefect record riêng liên kết source IDs. Frozen runtime/spec/reference/evaluator, per-task20inputs/2calls/64nativeobservations, history và cumulativecap314logical/942physical giữ nguyên. Shared native lock; merge read-only đủ164receipts/1454PUT, mỗi task/attempt tính một lần, vẫn so CF39/V153/EPDT113 không Plain. Independent review count3/ownership/merge PASS; source snapshots và imported manifests được self-check trước launch.

### Amendment2026-11-16 — userauthorized Gemini Pynguin mechanism pilot

User “m làm rồi cho chạy thử với gemini đi”. Research-only frozen-runtime pilot;
không phục hồi VF4/hybrid vào final/src sau retirement.12tasks chọn theo
sha256('pynguin-mechanism-v1:ID'),first12 task có savedPynguin seeds+coverage từ
Gemini source,không chọn theo detections. IDs4,17,47,63,1,40,55,33,112,9,10,49.

Single pynguin_guided arm;thêm giải thích DYNAMOSA structural coverage search,
branchdistance/searchbudget và limitations;LLM tìm spec-supported valuerelations/
boundaries khácseeds,không random perturbation/outofspec typecrashes. Mechanism
instructions giữ ở initial vàfeedback. Source packet,visibleowners,Pynguin seeds,
coverage/gaps reuse;0search/reextract/coverage observation mới trước freeze.
Guided inputstrùngPynguin bị loại như protocolcũ.20inputs/task,max2calls/task,
24logical/72physicalcap,4096completion,context12288đểappendguidancekhôngcắtsource;
evidence1024cap và native8s giữ nguyên. No extra completion smoke. Không thêm
independent hoặcbaseline generation;no chain/full run saupilot.

Primary incrementalPUToutside savedGeminiEPBVAv2+DTv2+CF+Pynguinpure union126;
cohortold1454PUT/157eligible,reportdenominatorpilotselectedandevaluatedonly.
Referencev0.1.10/evaluatorfrozen,spec125oraclefalsepositive/outoftype risks explicit;
extra gains provisional require specification audit,resource separate. Không
claim causalmechanismbenefit (contextcũngtăng,unmatchedbudget)hayfullbenchmark.
Modelgemini-3.1-flash-lite Vertex viaresearch_env+vertex_env. SourceGemini original
records unchanged. OnePrefectrecord/sourceconfig/progress/report,Completedonlyall12
haveevaluation+readonlyreplay. Authoredtoyendtoend0network/searchcheckPASS.

### Amendment2026-11-16 — userauthorized full mechanism-guided Gemini

User: “thử lại đi”, then “chạy lại full đi”. Full164slots/157eligible/1454PUT
samefrozenGemini cohort/reference/evaluator,notworkspacecurrent data. Single
mechanism-guided arm as previous pilot;no independent/Plain/DT/CF/Pynguin generation.
Clone frozen runtime;fix runnerhandoff only: producer writeslive manifest;
evaluator validatesmanifest read-only then runs cached generation/evaluation
without rewritinglive modelidentity. Test actualtwo-subprocessauthored fixture
beforelaunch;no livecalls/search inengineeringchecks. KeepretiredVF4out ofmain.

Reuse12pilotfrozen batches/23receivedresponses/105953knowntokens byteexact;
newrunrebuildspath/code manifest only,notinputs/requests.314logical/942physical
cumulativeuppercaps,≤291additionalresponses/919additionalattempts. Actual available
Pynguin evidence140tasks(≤280calls inclpilot);17unavailable+7cohortskip recorded
separately,notfalsezero.0newsearch/extraction;all evidence sourcehashes pinned.
20inputs/task4096completion/context12288/native8s/evidencecap1024unchanged.

Primary incrementalPUT outside savedGeminiEPBVAv2+DTv2+CF+Pynguinpureunion126;
report evaluatedtasks/PUTdenominators and old/referencefalsepositive caveats;
extra detections audit beforevalidbugclaim. Fullrequestdoesnot grantadditional
cohort/model/arm/autochain afterterminal. OnePrefectrecordwith pilot/source IDs,
source failedpilot untouched. No watch loop beyond existing artifactobserver.

### Amendment2026-11-16 — userresume after progress-log snapshot mistake

User “cho chay lại đi”. Full source083852 stopped on stage_events.jsonl checksum
because preparer pinned append-only progress logs. Fix frozen_generation_files
allowlist: packet/seed/coverage/informedpacket/inputs/freezes/decodedcatalogue and
receivedrequest/response/attemptJSON only; no events/logs/locks/pathmanifests or
native evaluation outputs in generation snapshot. Regression appendlog doesnot
change snapshot, seed/requestmutation still detected;two-processmanifesthandoff
regression remainsPASS. No paper/upstream/production change.

Continuationpreserves25responses25attempts/116431knowntokens and13frozeninputbatches;
task0evaluation9PUT completedbeforecontrollerfailure and retained byteexact.
Inheritedtask0 skippedbycontroller,oldresultusedin savedprogress union. Source
083852Failed retained unchanged;onlyknownmutablelog hash excluded in sourceread
verification. Code/config/request/input/evidence hashes stillverified;all native
source0evidence pinned. Samefull164slots157eligible/140available17unavailable+
7cohortskip,singlemechanismguidedGemini/context12288/input20/completion4096/native8s,
evidence1024.314logical942physicalcumulative,remaining289/917max,0newPynguinsearch.
One newPrefectrecord linkedsource,notgenericRetry;noextraarms/models/autochain/watch.


### 2026-11-16 — Gemini VF3 năm arm theo yêu cầu user

History chưa có Gemini VF3/replace/DTrollback. Chạy full157eligible/1454PUT,164slots với ep_bva_vf3,decision_table_vf3,ep_bva_vf3_replace,decision_table_vf3_replace,decision_table_vf3_prompt_rollback. HaiVF3cũ dùng wordinglarge-inputhistorical;baarmmới dùng rollbacksmall/bounded. Clone Qwencompletedruntime/reference/cohort;chỉ khôi phục promptprefix theo arm cũ,không workspace data mới. VertexGemini3.1FlashLite,4096completion12288context8s,seeds314159/271828,temp.7. Tối đa1570logical/4710physical;20retainedreplacement/30others. Frozenpertask rồi nativeisolatedconsumer/sharedlock,nooraclefeedback. Không rerunPlain/CF/V2;finalsavedcomparison reuseGeminiV2f4361b64 vàCFfull4. Chưa claim matchedcausal;chi phí/unknownattempts report thật.

VertexDT compatibilityamendment trướcworkload:SDKconverter dropsdynamicadditionalProperties,leavingemptyOBJECTschemasrejectedbyGemini. DT3arms usejson_object transport+compactDTcontractinprompt;localfullPydanticschema validation unchanged. EP2arms retainnativeJSONschema. Thisbackenddifference mustbereported,notclaimstrictdecodermatchedwithQwen. 0livecallsbeforeamendment.

Livecompatibilityamendment2026-11-16:EPnative task0HTTP400;sourceadf1eebaFailedpreserved. Task1all5armscompleted10responsesbeforestop. Newcontinuation3129a3a1 atgemini_vf3_five_arms_resume_20261116 keeps10responses/11attempts(1unknown400),archivesfailedcallso3percallbudgetcontinuesat2ratherthanreset. All5armsVertexJSONobject+compactrequiredfieldcontract/localfullschemavalidation;no selection/evaluator/budgetchange. Decoder differsfromQwen;task1nativeEPretainedmarkedpre-amendment. Cachedtask1freeze/sourcechecksPASSlocally,noextra completion/native.

### Amendment2026-11-16 — bounded rerun three Gemini429 failures

User “m cho chạy lại mấy chỗ fail đi”. Resume exacttasks69,73,133 only by
inheriting161saved taskrecords(137evaluated+24skip);keep265responses/288attempts/
23unknown/1171180knowntokens and allfrozeninputs.0newPynguinsearch/extraction.
Three exhausted requests eachhave3unknownHTTP429 attempts:69initial,73initial,
133feedback. User explicitrerun authorizes atmost3additional attempts ONLYthose
exactrequest identities(cumulative3→6),historynotreset.69/73newfeedback requests
keep original3cap.≤5newlogicalrequests/15newphysicalattempts;cumulative314/942
caps unchanged. Run-local RecordedModelCalls subclass temporarilysets cap6
for exact(task,call),restores default in finally;checkpointrequesthash unchanged.

Allmodel/settings/evidence/prompt/cohort/reference/evaluator unchanged. Task133
initialresponse reused,onlyfeedbackretried. Snapshotexcludesmutablestartedattempts,
sourceoriginalattempt/request files remain externalhashproofs. Parent fake-checkpoint
regressionmustprove firstnewattempt=4 anddefaultcap3restored. OnePrefectrecord
links sourcec16019aa;noautoextension/chain/modelchangeif429persists.

2026-11-16 usercontinue sauquota429:continuationgemini_vf3_finish14_20261116 giữ1488responses/1563attempts/150completedskipreceipts;chỉ14pendingtasks131PUT. ExplicitrequestIDgrantsmax6total cho14exhausted429calls(+42attempts),globalphysicalcap4752/logical1570unchanged;othercallscap3. Samefrozenruntime/sharednative lock/inputbudgets,prompts/reference unchanged. No rerun completedtasks/PlainCFV2.

### 2026-11-16 — User-authorized rescore sau sửa type admission

User “rescoer/rerun đi” sau khi enforce type hints/public-spec metadata. Scope:
rescore saved inputs/observations, không generation/search/extraction/inference mới,
không mở rộng task/input budgets và không sửa source runs. Nguồn Pynguin thuần
Qwen guided-repair114725, Gemini recovery235445, Gemini mechanism retry3_143000;
baseline Qwen EP/BVA v2+DT v2 và CF; Gemini full4 EP/BVA v2+DT v2+CF. Không khôi
phục retired VF4 implementation hoặc launch thêm arm. Full original task slots,
availability từng nguồn giữ nguyên; pending/unavailable không ghi thành0bugs.

Replay shared ReferenceOracleStage và PutEvaluationStage trên saved native
observations theo đúng input identity/repeat, strict source-input freeze proof;
transport replay không execute reference/PUT. Ghi artifact mới, report tiếng Việt,
Prefect record riêng links source runs,0newmodel/search/nativecalls. Giữ reference,
contract, timeout8s và seeds nguồn. Report type rejections, trước/sau valid-input
memberships, unique detected PUTs/kinds, lost witnesses, union gains và matched
availability denominators. Oracle false positives125 vẫn còn nếu input đúng type;
rescore này không sửa reference/spec semantics và không gọi mọi detection là bug.
Chuẩn bị authored regression so replay output với expected filtering/dedup/repeat
trước khi đọc rescore metrics. Không tự nối generation/evaluation run tiếp.

### 2026-11-16 — Gemini cho ba hướng concept sau sửa, bốn arm

User “chạy với gemini đi” sau khi yêu cầu cải thiện VF3 replacement, Obligation,
CF và public reasoning continuity. Scope fresh full164slots/157eligible tasks/
1454base-passPUT, chỉ ep_bva_vf3_replace, decision_table_vf3_replace,
spec_obligation và control_flow. Không thêm combined arm, Plain/V2 calls, Pynguin,
mutants hoặc dataset. Mỗi arm tối đa2logicalcalls/task và20retained inputs;
cap1256logical/3768physical attempts, tối đa3attempts/request, không tự reset/extend.
Gemini3.1FlashLite qua nativeVertex,4096completion/12288context,8snative evaluation,
temp.7,seeds314159/271828,confirm_first_failures. Snapshot currentcode+public-spec
type admission; original dataset/contracts/reference và fullcohort giữ nguyên.

VF3 Vertex dùng JSON-object+compact required-field contract và full local schema
validation, không native schema lỗi400trước đây. Hai vòng giữ public assistant
response và retainedinput/covers; checker exceptions có thể repair, unknown evidence
được bảo vệ. Primary treatment: membership_readytasks/eligible, task có actualswap,
sốinput swapped, phân biệt filledslot/no_new_coverage/unknown/no_redundant_witness.
Obligation dùng native seed/sampling→feedback trong2calls, không đóng basehit và
không bỏ generation khi metadata sai. CF construction-v2 reserve native budget
cho round sửa, native diagnostics về missed arc/verified-opcode divergence;
không gaps thì covered-path semantic fallback cùng budget. Không hồi sinh heavyv2.

Persist task inputs/freezes trước CPU consumer; generation tiếp tục task kế,
native execution của CF lẫn Evidence dùng cùngsharednative lock, không feed
oracle/PUToutputs về generation. Read-only manifest check trước cached evaluation,
read-only replay/source verification bắt buộc. Metric pending không tính0;
prompt_too_large/sharedpacket skip và infrastructure failures report thật.

Finalizer chỉ đọc saved observations cho baselineGeminiV2+Plain+CF và cácarmcũ;
lọc confirming witnesses theo current public types, đối chiếu PUTsets/spec/contract/
reference/expectedoutputs rồi mới union. Không native replay baseline. Report
wrong-value/exception/resource, novelPUT/taskcounts, usage/tokens/unknownattempts,
actual mechanism counts. Oldobligation là combinedV1/context18192, mới là
spec-onlynativefeedback/context12288; cùng các thay đổi type/selection khác nên
comparison descriptive, không isolated causal ablation hoặc matched-budget claim.

Prelaunch review independent:106engineering checksPASS; fixed2integration blockers
(VertexJSON-object và serialize Evidence.execute). Final frozen178files/runner/
controlhashes/selfcheckPASS;83additional Vertex/contract/typed-finalizer checksPASS.
Vertexcount_tokens readinessPASS,0completions trướclaunch. PrefectPending record
ca917440-63f5-403a-a0e3-7923d8f69500,3artifactsAPIverified;reuse cùngrecord để
progress/report,không duplicaterun. No automatic followup/retry extension/watch.

### 2026-11-16 — User yêu cầu sửa lỗi và phục hồi Gemini concept feedback

User “lỗi thì fix đi m” sau check envelope lỗi và CF17/31fail. Dừng dispatch
sourceca917440 sau task83, chờ children hoàn tất rồi giữ sourceCancelled/immutable.
Source có653receivedresponses/675attempts/22unknown,82frozen tasks; không xóa hoặc
ghi đè request/rawresponse/attempt. Chuẩn bị output mới, linksourceflow rõ ràng.

Root defect: compactVertexcontract diễn đạt inputlist và catalogue như hai giá trị
riêng. Prompt mới yêu cầu đúng một object {inputs,catalogue}; parser chỉ wrap complete
JSON list + optional comma + bare catalogue hoặc inputlist độc lập. Metadata thiếu
giữ unknown, trailing ambiguous data bịreject; semantic/type/localschema gates giữ
nguyên.328responses đọc lại được3985completeinputrecords, chưa đồng nghĩa valid
inputs hoặc detection. Re-decode historical received calls, không request inference
lại; lưu originalrequesthash và ghi rõ prompt dựng lại không được gửi. Historical
feedback chưa nhìn thấy state sau parserrepair; không claim causalfeedbackbenefit.

Giữ162completedCF/specgenerationfiles byte-identical. Chỉ archive combinedfreeze,
oracle/evaluation/result/summary và replacement-derived artifacts trong output mới;
freeze lại newunion rồi evaluation bình thường, input-executioncache reuse phù hợp.
Model/prompt của cácarmkhác, dataset/contracts/reference, timeout8s,20inputs/arm,
4096completion12288context và full157eligible1454PUT scope không đổi.

CF17solverintent không có result: spent1second được giữ unknown; không replay failed
dispatch hoặc suy infeasible. Explicitengine-recoveryproof kiểm importeddispatch
hashes, reuse completedsearch/native receipts; partialrecoverymới không có proof
bị từ chối. Engine infrastructure failures ghi unknown+diagnostic thay vì abort
toàn task; runtime giữ stderr cuối để chẩn đoán. Không unsandbox execution, không
sửa upstream engine hoặc reset native/solver caps.

CF31round1 có3unknown429attempts: chỉ exactrequestid
dc05c5e43347f7f13e4905fb763e433a54918955ebe95cfcea84be92ba7fd73d
nhận grantmax6total để phục hồi theo lệnh sửa; giữ3attemptscũ, nextattempt4.
Requests khác giữ3; không đổi tên call, không tự nối retry khi hết6. Globalcaps
1256logical/3768physical không đổi; RecoveryCalls kiểm physicalcap trước mỗi
prepare_generation. Expectedresponsesmới tối đa603, known675attempts được tính
trong cumulativephysicalbudget. Saved-onlybaselines không rerun.

PrelaunchindependentreviewCLEAR:64engineeringchecksPASS,13498sourceJSON/
2003callfiles/162preservedgenerations/178runtimehashes verified. Parent63checksPASS;
offline task0contractcheck với model/native forbidden khôi phục EP10/DT11inputs,
CF6/spec6giữ nguyên,653responses không đổi. SelfcheckPASS; không oracleoutcome
trước launch. FinalPrefectrecord mới reuse để progress/report, linksourceCancelled;
không automaticadditionalrun sau continuation này.


### 2026-11-16 — CPU64 vs128 trên frozen CF + obligation candidates

User đồng ý sửa source–target–feedback bundles, giữ diagnostics tối thiểu và
so64vs128native observations trên cùng saved pool; không gọi LLM/tokenizer/oracle.
Scope duy nhất coverage_spec_feedback Qwen full164slots/157eligible tasks,
407selected structural targets/28declared obligations/7620unique candidates,
2445selected inputs nguồn giữ nguyên. Không tính PUT gain hay sinh inputs mới.

Shared production scheduler chọn input–PUT pairs; candidate priority interleave
queues frozen round0 và round1 để prefix64 có cơ hội từ cảhai responses. Đây là
offline diagnostic trên fullpool cố định, không exact replay cap64cũ hoặc online
feedback test. Dùng một sequence tối đa128/task, đo tại prefix64và128. Dedup theo
call identity, exclude full recordedbase; labels của LLM seeds vẫn ởdirectqueue,
fallback owners chỉ gồm source analysis-surviving PUTs. Preserve1s/singleton,
4CPUworkers dưới sharednative lock theo batch; không reset budget hoặc rerun.

Primary: sốtargets/obligations hit trên cùngdenominators, unknown reasons,
observations thực và tổngsandboxseconds, walltime kể cả lockwait. Poolcoverage
không phải coverage của suite20inputs; finalinputs giữ nguyên, không causal
claim promptfix/generation efficacy. Predicates/checkers giữ supportdeclared,
512checks/5sbudget: exhausted giữunknown, khôngmiss. 128không tự làmdefault;
khuyến nghị sau khi đọc result và incremental cost.

Before outcome: independent read-only review yêu cầu labelledLLMseed giữdirect
queue và analysis-surviving fallback owners; đã sửa,4authoredcomparisontestsPASS,
129CF/spec/context/enginechecksPASS trướclaunch. Fullscope inventory preflightPASS;
source+runtime snapshots/hash giữ immutable, newPrefectrecord reuse flowID.

### 2026-11-17 — Fresh Gemini chỉ hai replacement arms theo user

User “check, :)) phải run lại chứ”, sau đó chọn “Chỉ hai replacement arm”.
Fresh full164slots/157eligible tasks/1454PUT, chỉ ep_bva_vf3_replace và
decision_table_vf3_replace. Mỗi arm tối đa20retainedinputs/task, initial20 và
tối đa10feedbackcandidates trong fixedsuite20; tối đa2calls/task/arm. Gemini
3.1FlashLite/nativeVertex,4096completion12288context/native8s,temp.7,
seeds314159/271828,confirm_first_failures. Cap628logical/1884physical attempts,
default3attempts/request;không retryextension hoặc tự nối run khác.

Không import response/request/generation/freeze/criteria từ run cũ; mọi initial
và feedback được gọi model mới. Vòng feedback thấy chính initialresponse và
checkerfeedback mới sau sửa envelope, giữ publicassistantcontinuity và strict
local schema/type/admission. Parserfallback vẫn đánh dấu repairs, không tính
split-envelope output thành strictwirecompliance. Initial/feedback responses
được persist trướcevaluation, taskfreeze trướcoracle/PUT;nativecache chỉ reuse
theo exactinput/jobidentity,không modelcache. Freshness mới là treatment khác
với continuationb5ee0568 đã re-decode653responses và còn tiếp tục độc lập.

Primary: novel detectedPUT ngoài saved typedGeminiPlain+EP/BVAv2+DTv2+CF,
wrong-value/exception/resource riêng, sốtask/validinput, actualcalls/tokens/
unknownattempts. Treatment:membershipreadytasks/eligible,swap_tasks/eligible,
sốswaps/candidates,repairreasons;metadatafailure không gọi là negativeefficacy.
Baselines chỉsavedobservations,lọccurrenttypes/provenance/spec/contracts/reference/
expectedoutputs trướcunion. Khácbudgets/context/admission vớioldruns nên không
claim isolatedcausal/matchedsuperiority. Không thêm CF/spec/Pynguin calls trong
freshrun;existingcontinuation không cancel hoặc sửa snapshot từ yêu cầu này.

Prelaunch181runtimefiles/runner/controlhashes/selfcheckPASS;45independentreview+
46parentcontract/envelope/budgetchecksPASS. Actualsnapshotpromptprobe0network:
ONEobject{inputs,catalogue},JSON-objectwire/localfullvalidator. Zeroimportedcalls,
nogenerationdirectory/RecoveryCalls. NewPrefect3a32113e-0754-4a26-9e3e-80d5e166e9f8
Pending/3artifactsAPIverified trướcfirstcompletion,updatecùngrecordkhôngduplicate.

### 2026-11-17 — User đặt retry429 sau một giờ

User “m cho chạy lại sau1h” sau kiểm số429 của hai run. Anchor request lúc
2026-11-16T17:40:46UTC; deadlinekhôngsớm hơn2026-11-16T18:40:46UTC tức
01:40:46ngày17/11giờViệtNam. Hai one-offretryrecord riêng, mỗi source mộtrecord:
fresh3a32113e→79685c2a-4723-4cea-a8a3-f21510a2fae0 và recoveryb5ee0568→
70d23ecd-0458-45b0-aabb-54c8387dae37. Source hiện tại tiếp tục, không cancel hoặc
sửa snapshot; retry chỉ chuẩn bị khi cảdeadline vàsource terminal/freeworkerlock.
Nếu source chưa xong sau1h thì chờ, không clone/checkpoint khi source đang ghi.

Sau khi sourcekết thúc, chọn tất cả task cógenerationfailure và canonicalrequest
stateunknown/http429/đúng3attempts cùngrequestdigest/chưaresponse, loại archived
attemptdirs và successful taskreceipts. Exactrequest được grantmax6total,next4,
tối đa3additionalattempts; newcalls còn thiếu trong selectedtask dùngdefault3.
Không reset/rename request, giữ receivedresponses và successful receipts; không
rerun non429task22 hoặc task hoàn tất, không thêm arm/task/dataset/backend.
Defaultmodel/context/input/nativebudgets giữ source; cumulativeglobalcapsfresh
628logical1884physical, recovery1256logical3768physical giữ nguyên. Model calls
bị chặn trướcprepare nếuphysicalcap hết. PartialCF dùng explicitdispatchhashproof
để giữ spent/cache; không gọi interrupted/unsupported là infeasible.

Scheduler/observer/recoveryhelper và enginefix được snapshot ngay, hashverify
trước và sauwait; sourceconfig/runner/snapshot pinned. Reprserializationfix một
dòng chỉ dùng trong runtimecopynew để tránh cùngcrash nếu inputliterals cóset;
không làm task22 thành eligible. Không recurrence hoặc thêmretryextension sau
lượt này. Không cóeligible429 thìCompleted/no-work với lýdo; preparationfailure
thìFailed trên cùngscheduledrecord. Successfulfullstate chỉ saueval/replay/final
comparison; non429/pendingkhác vẫnFailed/partialthật.

Prelaunch13independent/14parentchecksPASS, actualjob/observer/sourcepinning
reviewCLEAR, twoScheduled/3artifactseachAPIverified.0model/nativeworkload khi
tạo lịch. Preparedoutputfoldersgemini_fresh_429_after1h_20261117_014046 và
gemini_recovery_429_after1h_20261117_014046; localmachine/Prefect tiếp tục hoạt
động để one-offcoordinators thực hiện lịch. Không authorizethêmworkload ngoài
scope429continuation này.


## Amendment2026-11-17 14:57VN — Recovery replacement sau sửa treatment gate

User ra lệnh: “thế sửa rồi chạy lại đi, nếu không được thì đơn giản hóa lại,
tránh bắt output nhiều structured response”. Recovery chỉ hai arms
`ep_bva_vf3_replace`, `decision_table_vf3_replace` của source
`final/out/gemini_replacement_fresh164_20261117_115759`, Prefect
`31d45ffa-fc32-4cd9-bb93-ba91feae9b3a`; không mở rộng CF/Obligation/dataset.

Source đã Failed trước evaluation:157eligible generation failures,0/1454PUT
được evaluate;625responses/647attempts đã lưu. New output clone nguyên frozen
runtime/data và raw requests/responses/attempts; chỉ overlay hai file đã review:
`arms/catalogue_replacement.py`, `generators/methods.py`. Archive decoded
replacement batches/manifests/inputs trong output mới rồi re-decode received
responses; không sửa source output. Replay giữ exact sent request bytes; prompt
reconstructed không được coi là prompt model đã thấy. Fresh_generation=false.

Replacement protocolv3:input eligibility qua shared literal/budget/type/domain/
reference/oracle checks;metadata/treatment unknown/failed chỉ báo readiness,
không chặn cả task.0capacity candidate ghi not_exercised khi initial admission
known;selector/protection giữ nguyên,actualswap mới được applied. Efficacy
replacement vẫn chưa chứng minh nếu0swap. Không bắt model sửa metadata bằng
extra call hoặc sinh lại625responses. Nếu tiếp tục có lỗi contract, sửa/simplify
interface trong phạm vi này và ghi amendment trước outcome tiếp; không tự tăng
calls/cohort để tạo win.

Cùng157eligible tasks/1454PUT/164slots,fixed20inputs/task/arm,2logicalcalls/task/
arm,4096completion/12288context/native8s,temp0.7,seeds314159/271828. Cumulative
cap628logical/1884physical attempts giữ nguyên. Exact missing request hết3attempts
429 của task130 `decision_table_vf3_replace_initial` được grant tối đa3attempts
mới,max6total,next4,requestdigest và oldhistory giữ nguyên. Missing DTfeedback
nếu cần dùngdefault3; tối đa2logicalcalls mới,6physicalattempts mới theo trạng
thái source hiện tại. Không retry các received responses hoặc tự nối run khác.

Run mới có Prefect record riêng,continuation_source/source_flow_run_id rõ ràng;
report tiếng Việt,cost cumulative/new phân biệt,pending không thành0. Baseline
comparison saved-only,type-filter và source/reference proofs hiện có. Completed
chỉ khi đủ evaluation/read-only replay/final comparison. Generation persist
trước CPUevaluation;native sharedlock/cache exactidentity vẫn dùng.

Prelaunch engineering:103focusedchecksPASS sau sửa gate;313savedbatch
classification/156complete-taskgatechecks giữ inputs+selection+source hashes,
0model/native/oracle/PUT trong savedcheck. Recovery/calls/preparation/gate suite
38PASS; độc lập review treatment repair không có productionmustfix. New recovery
preparer/snapshot/caps được review độc lập trướclaunch;review findings và kết quả
selfcheck ghi trong output chuẩn bị. Amendment này được ghi trước outcome mới.

## Amendment 2026-11-17 — Full HumanEval Gemini, CF evidence v5

User yêu cầu “thử trên HumanEval đi m, bằng gemini full ấy” sau thảo luận nâng
contract/wire, CFG guard, data dependency, ordered trace và feedback evidence.
Run mới chỉ một arm `control_flow_obligation` dùng shared CF+spec/native-feedback
v5; không nhầm với frozen V1 hoặc engine-only control_flow. Full164slots,
157eligible tasks/1454base-passPUT;7shortfalltasks skip theo cohort hiện có.
Gemini3.1FlashLite nativeVertex;20retainedinputs/task,max2calls/task,
4096completion/18192context,temp0.7,seeds314159/271828,trace1s/eval8s,
64nativeobservations/task chia32/32,base-replaycap300/task,
32Hypothesisdraws/2s mỗiinstance. Caps314logical/942physical attempts;
không retryextension hoặc follow-up tự động.

Giữ V4 source-target-feedback bundles, context rotation, safe input/type/domain
admission và required semantic treatment gate. Bổ sung source-based guard
polarity/static may-return-dependencies; ordered selected guard-line observations
với frame/occurrence/primitive state trước dòng,64events/8locals;truncate không
ngắt execution. Không thu return values hoặc oracle outcomes trong generation.
Strategy JSON/wire validation reject riêng invalid sampler,giữ input/metadata
khác. Không khôi phục retired heavy-state validatedV2,không symbolic engine mới.

Dataset/contracts/reference clone completed Gemini baseline runtime;existing
HumanEval PUT cohort không sinh lại. Fresh generation,0response import.
Per-task freeze trước independent oracle/PUT;generation chồng CPUevaluation,
native sharedlock/cache exactidentity. Baselines Plain/EPBVA-v2/DT-v2/oldCF/
oldcombinedV1 chỉ saved artifacts,lọc current public-spec type admission;
report cả singles,paired gain/loss,union và extra ngoài Plain/EPDT/fullsavedunion,
wrong-value/exception/resource,actualcalls/tokens/unknownusage. Static target hit
không chứng minh semantic bug;khác context/yield/mechanism,nhiều evidence đổi
cùng nhau nên không causal matched-ablation claim. Requiredtreatment không có
native-measured obligation thì task lỗi/pending,không tự thay failed bằng0.

Snapshot/source/replay và final comparison phải verify trướcCompleted.
Contract/tracer tests dùng authored fixtures,không thêm model benchmark probe.
Independent prelaunch review bắt buộc theo shared working rules;giữ nguyên mọi
historical source/checkpoint và user worktree ngoài các file liên quan.


## Amendment2026-11-17 — Pilot V2 inputs-only, user “chạy thử đi”

User cho phép thử hướng V2 catalogue-off đã chuẩn bị; giới hạn8task eligible
chọn ngẫu nhiên với random.Random(20261117) trên sorted task IDs,không đọc
outcomes để chọn:6,38,52,56,60,78,89,90;77base-pass PUT. Chỉ EP/BVA V2 và
DT V2,16logicalcalls/48physicalattempts,default3/request,không grant thêm hoặc
nối full benchmark. Existing V2 catalogue-off là prior art,nothing novel claimed.

Gemini gemini-3.1-flash-lite/Vertex,1call/task/arm,20inputs/task/arm,
4096completion/18192context/native8s,temp0.7,seeds314159/271828. Giữ V2guidance/
soft examples; bỏ catalogue output request,covers và optional fault annotations,
output chỉinputs(namedarguments). Không feedbackround/replacement/CF/Obligation.

Baseline saved-only là gemini_catalogue_full164_20261112_193646. Copy original
public packet byte-identical để không tăng visible PUTs khi prompt ngắn hơn;
16/16baseline actually-sent messages đã kiểm trùng currentcatalogue-on prompt.
Copy original frozen dataset/contracts/reference và cohort vào output/runtime
mới;model responses baseline không import vào producer. Current implementation
của parser/admission/oracle dùng chung cho pilot và type-filter saved baseline.

Một newPrefectrecord cho sourcepilot,progress/report tiếng Việt,pending truthful;
Completed chỉ khi8tasks evaluation+read-onlyreplay+savedcomparison xong. Report
validinputrecords,calls/knowntokens/unknownattempts,wrong-value/exception/resource,
gained/lost/sharedPUT và union trên77PUT. Concept guidance có nhưng mechanical
concept coverage off/chưa đo,không ghi0hoặc100%. So với historical sample khác
randomdraw nên không claim causal effect hoặc fullbenchmark superiority. Không
chọn thêm task hoặc retune theo các lỗi đọc được để cứu kết quả yếu.

Prelaunch độc lập review clear,16baselinepromptsverified,unitpreparer/config/
finalizerfixture và V2integration kiểm trước completion đầu. Runtime/source/
control hashes frozen;source baseline/checkpoints không sửa. Controller reuse
per-task freeze/producerCPUoverlap và native sharedlock/cacheexactidentity.
Default3attempts/request và16callslots tạo hardcap48attempts;khôngextra repaircall.


### Amendment2026-11-17 — Pilot parser recovery,0completion mới

Trong pilot8 gốc,task38EP response có19complete input records rồi một expression
nối chuỗi ở record cuối. Whole-response parser loại cả batch,không phải model
không sinh input. Sửa routineIOtrongCatalogueArm.decode_response khi cataloguefalse:
reuse bounded read_catalogue_response để lấy complete literal records trước tail;
không evaluate expression/không tạo missingvalues. Một focusedregression và saved
responseaudit xác nhận19record được cứu,rawresponsehash không đổi.

Sourcepilot frozenruntime/metrics giữ riêng. Sau source terminal/freeworkerlock,
parserrecovery mới clone source runtime và overlayONLYclassical.py,copy16requests/
responses/attempts,verifyallsource/control/importhashes. CachedModelCalls làduy
nhất ở producer,không modelconstructor/preflight/tokenizer/completion;0newcompletion
cap,không tăng16logical/48physical budget. Cùng8tasks77PUT/native8s/20inputs,
re-evaluation qua cacheexactidentity rồi read-only replay/finalcomparison. New
Prefectrecord liên kết source. Source gốc phải có đầy đủ16responses,mọi response
thiếu làm preparationfail thay vì gọi modelbù. Không nối full/newtask/retune.

31focusedchecksPASS,independent reviewer replay16/16savedrequestsclear,task38
19completeinputssalvaged. Giữ source raw-parser result riêng và gọi phần cải
thiện này là parserrepair,không gán thành tác dụng riêng của promptinputsonly.
Finalreport đưa chi phí model của pilot16responses làm total;recovery0calls mới.

Prelaunch evidence-v5:117focusedtestsPASS;final9newregressionsPASS,independentreviewer58authoredchecksPASS. Actual isolated frozenfixture native→feedback→obligationtreatment→reference/PUT→immutable replayPASS,0modelcalls. Reviewer sửa inline-return polarity thànhunknown và bound diagnostic counters/returnedframes;không cònmustfix. Source/control hashes và pinneddata identityPASS. Decorated callable wrappers/multilineguardheaders chưa hỗ trợ;ASTreview không có trong currentbase-passcohort. Chưa có efficacy outcome khi ghi amendment.

Đính chính count trước launch:finalnewregression suite có8casesPASS,không phải9;117focused vàreviewer58PASS giữ nguyên. Observer dùng orchestrationvenv cần PYTHONPATH repo root khi chạy script ngoài package;0workload trướclaunch.


## Amendment2026-11-17 — Full V2 inputs-only theo user “chạy full”

User cho phép mở full hướng V2 inputs-only sau pilot8. Giữ hai arms ep_bva_v2,
decision_table_v2,catalogueFalse,khôngfeedback/replacement/CF/Obligation.
Tất cả157eligible tasks/1454base-passPUT;7trong164cohortslots bị loại theo
cohort gốc,gồm generation_shortfall/no_base_pass,không lọc theo kết quảtestmới.

Newoutput/newPrefectrecord,continuation_source là completed parserrecovery
c209034c-ed54-4064-a7d6-7b9f46aa2b76. Clone nguyên frozen runtime/data/reference
của pilotđãreview,0overlays;import nguyên16receivedrequests/responses/attempts
của8pilot tasks,khôngimport decodedbatches/evaluation để che lỗi. Giữ original
publicpackets của savedV2 trên157task;314baseline actualsentprompts đã review
khớp currentV2catalogue-on,16pilotrequests khớp catalogue-off. Không regenerate
receivedresponses,không feed knownPUToutcomes hoặc oracle vào generation.

Gemini gemini-3.1-flash-lite/Vertex,1logicalcall/task/arm,20inputs/task/arm,
4096completion/18192context/native8giây,temp0.7,seeds314159/271828. Cumulative
cap314logical/942physicalattempts,default3attempts/request,noextension.
16responses imported nên còn298newlogicalslots,mỗi slotmax3attempts. Không
thêm arm/task/dataset/backend/budget;full này không tự nối bất kỳ run khác.
Bounded complete-input-record salvage của pilotrepair giữ nguyên;không evaluate
expressions hoặc tạo input thay thế. Runtime/control/import hashes kiểm trước
vàsaugeneration,reuse nativecache exactidentity vàsharednativelock.

Report tiếng Việt trênPrefect ghi pending truthfully,cumulative/new calls/tokens,
validinputs,perarmvàunionPUT,wrong-value/exception/resource,gained/lost/sharedso
savedV2 đã typefilter. Táchpilot8 vàremaining149task trongreport; đây là followup
đã thấypilot,không held-out/causal confirmation. ChỉCompleted khi157evaluation+
read-onlyreplay+finalcomparisonxong. Conceptguidance/softexamplesgiữ,mechanical
conceptcoverageoff/unmeasured,không0hoặc100%. Baseline saved-only khônggọi lại.

Prelaunch scoped32testsPASS vàindependentreviewrequired;sourcefrozenpilot,
originalpacket/data/importproofs vàselfcheck được verify trước workload. Nếu
lỗi429hếtdefaultattempts,giữfailed/pendingvàledger,không tựreset hoặcgrantthêm.

## Amendment2026-11-17 — Retry exact failed tasks 17/144

User cho phép “cho chạy lại 2 task lỗi”. Đây là continuation bounded,không phải
Audit script: audit chỉ read-only; workload dùng output recovery mới
`final/out/gemini_v2_full157_retry17_144_20261117_190000` và Prefect record mới,
liên kết source full run `47984d6b-8210-4dc0-82c2-f2878ee53c7a`.

Source failed partial có đúng hai generation failures HumanEval/17 và /144:
chỉ `ep_bva_v2` initial request ở mỗi task có3attempts `429` cùng request_id,
không response. Recovery giữ 155 successful task receipts/generation artifacts,
copy frozen runtime/data/reference/cohort,archive metadata của đúng hai task,
grant exact request max6/next3,loop chỉ hai task. Cumulative source cap314logical/
942physical giữ nguyên;không retry task hoàn tất,không thêm arm/task/budget,
không dùng known PUT outcomes. `RecoveryCalls` giữ request/attempt identity và
source response ledger; retry mới chỉ được ghi nếu Vertex trả response.

Self-check recovery PASS trước workload. Independent review phải clear trước
launch; report tách retry cost/response và giữ source partial metrics. Completed
chỉ khi hai task generation/evaluation/read-only replay/final comparison pass;
nếu retry tiếp tục429, giữ Failed/pending thật và không tự extension lần nữa.

## 2026-11-17 — Catalogue reflection theo slides, trước workload

User cho phép implement + chạy Gemini full HumanEval và yêu cầu enforce EP/BVA/DT trong reflection. Hai arm mới `ep_bva_reflection`,`decision_table_reflection`: lượt1 catalogue/public rationale/initial inputs; lượt2 nhận exact original messages + raw public assistant response, checklist EP/BVA/DT bắt buộc theo slides, chỉ trả final inputs≤20. Không hidden reasoning,không tool membership/evidence feedback hoặc oracle/PUT outcomes trong generation. Metadata sai vẫn evaluate valid inputs; semantic compliance unverified. Context overflow báo incomplete,không truncate history. Xem research/catalogue-reflection-2026-11-17/README.md cho primary papers và mapping slides.

157eligible tasks/1454base-pass PUT,164cohort slots;Gemini3.1flashlite/Vertex,4096completion/18192context,temp0.7,seeds314159/271828,native8s/input;2calls/task/arm,cap628logical/1884physicalattempts,final20inputs/task/arm. Fresh628slots,0importedresponses. Snapshot code riêng; pin data/reference/cohort và exact public packets từ saved catalogue baseline. Generation persist và freeze đủ hai arms của task trước independent oracle/PUT;CPU consumer overlap task tiếp theo. Không mở thêm workload/automatic retry extension. So saved catalogue-on V2 và inputs-only bằng type admission hiện tại,gained/lost/union/singles,wrong_value/crash/resource,valid input records,calls/tokens. Different call budget/historical comparison,không causal superiority claim. Known MAD reference issue báo caveat. Prefect một record/output,Completed chỉ sau evaluation,replay và comparison xong. Independent read-only review áp dụng must-fixes trước launch.

Prelaunch review amendment: reviewer read-only xác nhận history/cap/snapshot và replay paths; kiểm tất cả157tasks của cả hai saved sources, tái hiện unions122/118PUT,không workload. Must-fix config resolved:ghi rõ input_temperature0.7,input_seed314159,reference_seed271828 thay vì chỉ dựa dataclassdefaults. Usage helper nhận cả `_reflection`,regression test2calls. Observer chỉCompleted khi có comparisonJSON/report. Focused81checksPASS;semantic compliance vẫn unverified. Generation freeze ghi trước evaluation;không thêm guard cấm sửa savedinputs khi evaluate (theo user clarification).

Recovery amendment trước outcome: launch đầu nhận16responses/4tasks nhưng0evaluation vì controller template gọi freeze_inputs đã được pipeline đổi tên. Đã dừng controller/child,source350ecff5Failed,giữ checkpoints. Sửa API thành record_input_hashes. Decoder reflection normalize direct parameter maps thiếu envelope `arguments` qua CallBuilder, dùng complete-record salvage có sẵn;không evaluate arithmetic hoặc đổi prompt. Catalogue prose được chấp nhận cho presence diagnostic theo chính contract ban đầu. Reviewer replay độc lập cả16responses xác nhận exactrequest/history,0model/nativecalls;countsfinalEP/DTt0=9/20,t1=20/20,t2=18/20,t3=19/19. Thêm test chạy actual generatedcontroller generation trên authoredfixture;sourcewriterlock kiểm trướcimport. Recoveryoutput import16receivedresponses+attempts,612logicalslots mới còn lại,cumulativecap628/1884khôngđổi. Không import bad parsedinputs,không tune theo PUToutcomes,chưa outcome nào được tính. ReviewPASS,13focusedrecoverychecksPASS.


## 2026-11-18 — HumanEval-X Java, Gemini Plain và Decision Table V2

User yêu cầu chọn C++ hoặc Java dễ triển khai harness hơn rồi chạy Gemini với
plain + decision_table_v2, không EP/BVA; xác nhận tự launch trong scope đã cho.
Chọn Java164; không tạo thêm run C++ hoặc nhánh kế tiếp. Canonical cohort C++
đã hủy ở Prefect d7eae726 trước workload,0attempts/0completion; canonical source
không được dùng làm PUT cho comparison này.

Dùng Gemini3.1FlashLite/Vertex sinh độc lập tối đa10PUT/task từ spec/declaration,
count là upper limit, không refill. Một writer request/task,4072completion,
temperature.9,seed20261030; public example tests/native8s lọc base-pass PUT.
Sau generation, plain và decision_table_v2 dùng chung các base-pass PUTs,
20inputs/task/arm,4096completion/context18192,temp.7,seed314159+task,2reference
observations và2PUTobservations,input độc lập trong sandbox. Task32 nonunique
root oracle unsupported bị skip trước model; reference public tests fail cũng
skip rõ lý do. Contract/spec admission và base duplicate filtering vẫn pending.

Cap164writer+328tester logicalrequests; tối đa1476physicalattempts gồm retries3,
không retry extension. Trần20USD theo conservative reservation1USD/Mprompt+
5USD/Moutput,giữ reservation cho unknown attempts; đây là budget proxy,không
phải invoice estimate. Không sinh mutation hoặc đưa oracle outcomes vào model.
Raw requests/responses/attempts và actual tokens đều lưu; cùng một Prefectflow
bao trọn writer/base/input/reference/PUT evaluation và progress/report tiếng Việt.
Snapshot runtime/source data riêng; existing runs/snapshots không sửa.

Prelaunch review phát hiện và đã sửa: prepare import dùng sai venv,thiếu explicit
PYTHONPATH;public Solution compile sai filename;init failures và budget exhaustion
thiếu diagnostic. IndependentreviewGO,14focusedchecksPASS;parent120checksPASS.
Không benchmark/model calls trong engineering review. Kết quả là confirmed
reference disagreement,chưa là verified semantic bug hoặc causal superiority.

## 2026-11-18 — Catalogue-only → pure EP/BVA/DT, chỉ chuẩn bị

User chốt “catalogue1lần rồi lần sau thuầnEP/BVA/DT”. Hai arms mới tách catalogue-design khỏi input-instantiation. Lượt1 chỉ JSONcatalogue + publicrationale,không initialsuite;accidentalinputs bị bỏ. Lượt2 nhận exactoriginalhistory+rawassistantcatalogue,sinh final≤20inputs bằng weakEP/normalBVA hoặc DT cơ bản,không V2faultguidance/softexamples/selfreview. Catalogue theo specification,không searchcap thành boundary. Không toolmeasurement hoặc oracle/PUTfeedback trước generation. Metadata error chỉ diagnostic,không chặn validsecondinputs;semanticcompliance unverified,không claim enforce bằngproof.

Preset chuẩn bị full164slots/157eligible tasks/1454PUT,2arms,2calls/task/arm,cap628logical/1884physicalattempts,20inputs/task/arm,4096completion/18192context,temp0.7,seeds314159/271828,native8s. Model theo console,không tự launch Gemini hoặc model khác. User chưa cho phép lần chạy mới;không có output/score mới. Khi launch cần snapshot/runtime và Prefect theo rules. Existing reflectioncheckpoints giữnguyên. IndependentreviewPASS (code/config),semanticlimits đãnêu;deployment schema dryrun15presetsPASS,không registerdeployment.

## 2026-11-18 — User cho phép full catalogue-only → pure inputs

User làm rõ “ý là chạy full đi”,thay pilot8 vừa được nhắc;không launchpilot. FullHumanEval157eligible tasks/1454base-pass PUT từ164slots;haiarms ep_bva_catalogue_then_inputs và decision_table_catalogue_then_inputs,Gemini3.1flashlite/Vertex,2calls/task/arm,final≤20inputs/task/arm. Cap628logical/1884physicalattempts,4096completion/18192context,temp0.7,seeds314159/271828,native8s/input. Freshgeneration,0importedresponses. Không thêm Plain hoặc freshcontrol/pilot/round1evaluation.

Lượt1catalogue+publicrationale,khôngsuite;historynguyênvẹn cho lượt2 sinh inputs bằng EP/BVA/DT cơ bản. Accidentalfirstinputs bịbỏ;metadata sai khôngblock validfinalinputs;semanticcompliance chưa kiểmchứng. Originaldata/reference/cohort và publicpackets từsavedV2;runtimecode riêng. Sau generation đủ2arms của taskmới queue oracle/PUTCPUconsumer;sharednativelock,khôngoutcomefeedback. Baselinescatalogue-on122/inputsonly118/priorreflection109 chỉđọcsavedartifacts;reportgained/lost/union,wrong_value/crash/resource,validinputs,calls/tokens và actualhistory/cataloguepresence. Differentprompt/budget/historical,khôngcausalclaim. KnownMAD/Unicodeoracleissues ghi caveat.

Theo simplifiedpipelineuser:khôngrestoresource/freeze/oldmanifestguards hoặc claimreplay khi khôngchạy. ObserverCompleted chỉsauevaluation+savedcomparison;legacyverificationreceiptfields=null. Reviewread-only phát hiện successmessage cũ claimreplay dùđãbỏ;đãsửa trướclaunch. Generation/evaluationentrypoints được test với authoredfixture,currentAPI. Prefectmộtrecord/output,progresspending khôngghi0;khôngnốirun hoặc retryextension saufull.

Prelaunch kiểm tra hoàn tất:35focusedchecksPASS,gồm generatedcontroller generation+evaluation hiện tại và finalizer hai phases/priorreflection. Các must-fixesreviewđã xửlý:fixtureCONFIG,success/selfchecktext khôngclaimreplay/sourceverification. Fulloutput `final/out/gemini_catalogue_then_inputs_full157_20261118`,PF6471d057-d17b-4214-b1e7-33407764207a;controllerdetached2088472/observer2088477.0pilotlaunch,0importedresponses,sourcefreshfullđượcusercho phép. Prefectrecord+3artifacts xácminhAPItrướclaunch;Completed chỉsau evaluation và savedcomparison.

## 2026-11-18 — Port Java Control-flow và thêm EP/BVA V2 trên saved PUTs

User yêu cầu “port sang và chạy thêm EP+BVA v2”. Lượt này chỉ sinh inputs cho
`control_flow` và `ep_bva_v2` trên đúng 152 task / 206 base-pass PUT của source
`final/out/humaneval_x_java_gemini_plain_dt_v2_20261118_012100`, Prefect
`c0992de7-b7c4-43b9-bf6c-eb08eadb57f7`. Giữ nguyên sources, public-test receipts,
task packets và 12 source skips; không refill PUT hoặc mở thêm C++/task/model.
Plain39 / DT43 / union47 là saved baseline; không gọi lại baseline generation.

Gemini3.1FlashLite/Vertex, 20 final inputs/task/arm, 4096 completion tokens,
18192 context, temperature0.7, seed314159+task; native evaluation8s/input,
2 reference và2 PUT observations như source. EP/BVA V2 dùng shared arm guidance,
1 logical call/task. Java CF giữ concept/instruction+seed inputs → Hypothesis
sampling → actual native coverage → tối đa2 rounds có nguyên public assistant
response. Cap456 logical /1368 physical attempts gồm default3attempts/request;
trần20USD bằng conservative full-output reservation1USD/Minput+5USD/Moutput.
Unknown attempts giữ reservation; không retry extension hoặc tự nối run.

JaCoCo0.8.13 upstream agent/CLI, pinned SHA256, source không rewrite. C1 là
uncovered executable Java source lines; C2 là source line có ít nhất một JVM
branch outcome mới so với public-test baseline. Target hit không khẳng định mọi
branch trên dòng đã phủ. Không port Python exact arcs, ordered paths, MC/DC,
static CFG hoặc def-use; các phần này `not_measured`. Targets tối đa6/task,
chia đều owners; sampling32draws/concept/2s, native tối đa64input–PUTpairs/task,
round0≤32pairs, trace1s/input. Inputs selected ưu tiên novel target hits rồi
signature-valid attempts. Không gửi return values/exec data hoặc oracle vào
model feedback; metadata sai không được loại direct input hợp lệ. No-gap,
coverage-unknown và prompt-too-large có status riêng, không coi là100%coverage.

Freeze đủ hai arms trước independent reference/PUT evaluation. Runtime và jars
snapshot riêng; shared native lock giữ nguyên. Report tiếng Việt: per-arm valid
input memberships, detected PUT/206, novel/shared/union ngoài saved47, actual
calls/tokens và wrong-value/exception/resource; resource witness overlap giữ
riêng. Spec admission, base duplicates và concept semantics còn pending;
reference disagreement chưa là verified semantic bug. So sánh descriptive,
không matched-budget causal claim; C1/C2 gain cũng không phải PUT bug gain.
Một Prefect record/output, config/source/progress/report thực tế; chỉ Completed
khi evaluation đủ206PUT và saved baseline comparison/report đã hoàn tất.

Independent read-only review GO trước workload:28 focused tests PASS, không
LLM/benchmark calls trong review. Must-fixes đã áp dụng: malformed strategies
không crash/drop direct inputs; baseline tests rỗng là unknown; output serialization
error vẫn giữ JaCoCo coverage; source snapshot metadata cập nhật sau khi copy
exact task packets. Real JaCoCo tests xác nhận baseline union (branch cũ không
gain), short-circuit progress chưa là full branch coverage, và feedback không có
returned values. Mọi engineering native tests dùng authored fixtures.

## 2026-11-18 — Java spec-admission fix và saved-only audit

User yêu cầu “thế làm đi” sau khi phát hiện raw gains có witness ngoài spec.
Thêm gate dùng lại trusted EvalPlus contracts và public input types cho đủ164
Java public packets; map tham số theo vị trí, normalize Java numeric values theo
typed serializer, không suy constraint từ PUT/reference outcomes. Contract chỉ
chạy trong sandbox validate-only; invalid/unknown không vào CF native feedback,
selection hoặc reference/PUT evaluation. Unknown timeout/error/missing metadata
báo riêng. Giữ original union indexes và raw generation inputs; frozen runtime
mới có contracts.json. Full natural-language spec completeness chưa chứng minh.

Đây là bug fix sau khi đã biết kết quả Java và targeted audit4PUT; không coi là
held-out hoặc causal validation. Không gọi thêm Gemini, không sinh PUT/input mới
và không launch/rerun reference/PUT benchmark. Sau engineering tests/review,
chỉ kiểm trusted admission trên saved inputs của completed source Plain/DT
c0992de7 và EP/CF cbe82791, rồi lọc các saved failing-index sets; raw outputs và
historical runtimes giữ nguyên. Ghi receipts/output view mới và publish audit
vào existing Prefect record, không tạo duplicate experiment record.

So sánh cả4arms phải dùng cùng gate; report ghi raw/gated input memberships,
invalid/unknown, detectedPUT/206 và union/gain. Missing/unknown không tính valid
hoặc thành bằng chứng PUTpass. Mọi metric nói rõ trusted-contract scope, không
gọi là full semantic correctness. Cap mới:0model/0reference/0PUTcalls;chỉ trusted
validator execution với timeout0.25s/input. Không tự nối run generation.

Review độc lập GO trước saved audit:22focusedchecksPASS;parent57benchmark
engineeringchecksPASS,latest15checks gồm frozen-runtime164contractbindings và
unstable-reference projection PASS. Must-fix stable-reference set áp dụng cho
cả detected/pending witness sets trước audit. Không benchmark/model/reference/
PUT execution trong review; chỉ authored fixtures và validate-only contracts.

## 2026-11-18 — User cho phép rerun riêng Java CF với admission từ đầu

User nói “ờ, thế chạy đi, mà DT, EP có gain gì k” sau khi chốt chỉ cần rerun
CF để feedback/selection dùng gate từ đầu. Fresh generation chỉ `control_flow`
trên đúng152task/206PUT từ completed EP/CF sourcecbe82791. Không import CF
responses, concepts, sampled/selected inputs hoặc feedback cũ. Giữ exact saved
cohort/public-test receipts; runtime, jars, trusted contracts và task packets mới
snapshot riêng. Không writer/refill hoặc rerun Plain/DT/EP generation/evaluation.

Gemini3.1FlashLite/Vertex,20finalinputs/task,2rounds,4096completion/18192context,
temp0.7,seed314159+task(+round),JaCoCo0.8.13,6selectedtargets,32Hypothesisdraws/
concept/2s,64nativeinput-PUTpairs/task,trace1s/input,evaluation8s/input,
2reference+2PUTobservations. Gate public-spec types/trustedcontracts chạy trước
mọi CF native feedback/selection và reference/PUT;validator0.25s/input,
invalid/unknown bị loại và lưu reason. No-gap task không gọi model. Cap304logical/
912physicalattempts,default3attempts/request,20USDconservative reservation theo
1USD/Minput+5USD/Moutput;unknownattempts giữ reservation,không retryextension.

Primarybaseline là saved Plain/DT gốc c0992de7 và saved EP ở cbe82791,lọc cùng
admission;oldCF không được nhập baseline này. OldgatedCF chỉ dùng để báo riêng
gain/loss/net. Known saved gatedsets trước rerun:DTvsPlain gain3/loss6/net−3;
EPvsPlain gain1/loss4/net−3. DTunique3 và EPunique1 ngoài hai arm còn lại.
Đây là comparison sau khi đã xem source outcomes,không held-out/causal proof.
Known caveats:Java111space-token ambiguity/referenceemptykey,Java123reference+
PUToverflow tại n2147483647;không đổi contracts/cohort theo các outcomes này.
Java134tab-vs-space và EPJava137near-equal có witness bám publicspec.

Prefect record mới cho fresh CF run,liên kết source/baselines;config/progress/
usage/report tiếng Việt. Report diễn giải gain/loss/net;absolutecounts/mẫu số
trong bảng,unknownpending riêng. Chỉ Completed khi đủ206PUT evaluation,baseline
comparison và report hoàn tất. Không mở thêm benchmark hoặc nối run sau đó.
Parent59engineeringchecksPASS,CLIhelp/importPASS;review độc lập phải GO trước
launch. Mọi prelaunch execution test dùng authored fixtures hoặc validate-only
contracts,không realmodel/reference/PUT benchmark calls.

Prelaunch review GO cho scope CF-only:independent33checksPASS,parent59PASS,
preparedsource152/206/pinnedjars và caps304/912/20USDverified read-only. Must-fix
report đã áp dụng:giữ `input_admission` preselection diagnostics trong CFgeneration
summary để invalid/unknown candidates không bị che bởi selected-suite counts0.
Regression report test kiểm invalid3/unknown2 được giữ. KnownJava111/123 caveats
được ghi trong finalreport;không sửa contracts,cohort hoặc sourceoracle.

## 2026-11-18 — Gemini original CF trên MBPP+ (user authorized)

User yêu cầu chạy Gemini với CF gốc sau comparison MBPP+ Plain/EP+BVA/DT.
Scope cố định255task/2140base-passPUT từ baseline e048b188;123baseline skips
không mở rộng. Một arm coverage-concept-discovery-v1 từ frozen Gemini originalCF,
không obligation/engine/construction. Max2calls/task,20selectedinputs/task,
4096completion/18192context,temp0.7,seed314159,trace1s/eval8s,64nativeobservations,
32Hypothesisdraws/2s perconcept. Caps510logical/1530physical/5100inputslots;
không retry extension hoặc followup run. Baseline và base-pass receipts chỉ reuse;
không sinh PUT hoặc gọi lại baseline. Primary: PUT mới ngoài Plain/EPDT/all3,
report gained/lost/net và wrong-value/exception/resource/harness, inputs/calls/tokens.
Descriptive saved-union comparison, không matched-budget claim/spec-bug proof.
Output final/out/gemini_mbppplus_original_cf_20261118. Bridge publicspec+literalcalls
reuse V1 MBPP integration; CF arm/prompt/schema/analysis byte-identical original.
Prelaunch review: targetcounts None giữ unknown riêng; reject non-JSON-safe concept
metadata tại bridge trước feedback, direct inputs vẫn giữ. Normal+complex authored
end-to-end checks real CF/Hypothesis/native/reference/PUT/replay/classifier PASS,
0live model calls trong engineering. Không thay source/checkpoint historical runs.

## 2026-11-19 — MBPP+ Pynguin thuần và Gemini guided từ Pynguin

User yêu cầu chạy hai arm trên MBPP+ rồi điền bảng Wrong-value / Exception / Timeout. Dùng đúng 255 task và 2.140 base-pass PUT trong baseline Prefect `e048b188-0b00-4863-bfc8-eb2fdcde73d1`, lấy đủ các task đã evaluation, giữ code và oracle của cohort. Pynguin 0.48.0 DYNAMOSA, seed 17, 10s search/30s owner wall, soft cap 200 test executions, tối đa 64 extracted calls/owner, 10 owner/task và 20 retained inputs/task. 0 model calls cho Pynguin thuần.

Guided dùng snapshot mechanism-guided HumanEval với Gemini 3.1 Flash Lite qua Vertex. Scope tối đa 2 calls/task, 510 logical calls, 1.530 attempts, 4.096 completion / 12.288 context tokens, temperature 0.7, seed 314159. Dùng tối đa 6 seeds từ batch Pynguin đã lưu, 1.024 tokens Pynguin evidence và tối đa 64 coverage observations/task với trace timeout 1s. Thiếu seed thì skip guided và lưu lý do. Prompt ghi rõ MBPP+ thiếu executable domain contract. Hai arm dùng signature admission và stable MBPP reference, cùng 8s/input và hai execution observations. Base-pass inventory được đọc lại từ baseline đã hoàn tất. Chỉ dùng base coverage nguồn nếu base pass và code trùng. Freeze từng task/arm trước oracle và PUT evaluation. Guided đọc seed trước evaluation, không dùng oracle outputs.

Đếm PUT riêng từng arm và union trên task giao nhau. Mỗi PUT nhận loại mạnh nhất Wrong-value → Exception → Timeout. Exception bao gồm MemoryError/RecursionError. Harness-only lưu riêng và loại khỏi ba cột. Task lỗi hoặc thiếu evidence có lý do và mẫu số pending riêng. Ghi hai Prefect run IDs và báo cáo tiếng Việt. Bảng cập nhật từ saved receipts sau khi cả hai worker kết thúc. Scope không có LargeInput hay HumanEval generation.

Amendment trước workload. Review độc lập xác nhận cohort, signature và evaluator hai lượt. Đọc trạng thái pure trước khi quét seed để tránh race ở task cuối. Phân biệt response không dùng được với input list rỗng có chủ ý. Tái dùng parser recovery cho các complete literal records trước phần JSON bị cắt. Nếu một arm lỗi lúc startup, vẫn xuất số đã evaluation của arm còn lại. Worker failure giữ lý do riêng. Test fixture Pynguin upstream, seed dedup, tuple và two-repeat classification đã pass. Workload dùng 8 worker task Pynguin và 4 worker task guided evaluation, với một Gemini producer.

### 2026-11-19 — Guided transport continuation

Snapshot ban đầu dùng `modular/calls.py` từ runtime cũ cùng Vertex transport hiện tại. Khi Vertex trả 429, hai lớp `TransportError` khác nhau khiến checkpoint để attempt ở `started`. Dừng riêng guided tại lượt request đang chạy, sau khi arm Pynguin kết thúc. Giữ mọi response, attempt và evaluation receipts trong output continuation, lưu cùng nguồn Prefect. Sửa import sang checkpoint hiện tại. Retry chỉ task còn thiếu trong cap gốc, tính attempt đang mở là attempt đã dùng. Hai CPU workers đo coverage trước lượt gọi model kế tiếp. Prompt, task/PUT cohort, độ dài timeout, model và giới hạn calls/inputs giữ theo config gốc.

### 2026-11-19 — Admission repair trên saved guided inputs

MBPP/297 dừng trước mọi reference/PUT receipt vì một literal nằm ngoài input validator. Áp dụng cùng CallBuilder theo từng record và ghi indices bị reject. Chấm phần còn hợp lệ từ batch đã lưu. Tập repair chỉ gồm task có đúng lỗi validation, còn input hợp lệ và chưa có reference/PUT receipts, xác định từ artifact đầu vào. Dùng output mới, bảo toàn batch/result cũ và giữ tất cả task receipts đã evaluation. Zero Gemini, tokenizer hoặc Pynguin search calls cho repair.

## 2026-11-21 — Pilot 15 task và Qwen Full164 cho Z3

User yêu cầu GPT-6 Luna low qua subagent thử pilot, theo dõi và sửa interface nếu lỗi parse, chỉ đặt lịch Qwen Full164 05:00 ICT sau khi đạt. Pilot dùng 15 task số nguyên với một bộ 45 predicate cố định và một bộ 45 predicate do Luna viết từ public spec. Tool sinh toàn bộ concrete input. Z3-only gọi trực tiếp từng predicate và Hypothesis-only dùng 64 draw/task, cùng contract và bounds. Query cap 3/task, tối đa 250 ms/query, 2 giây/task/tool, seed 314159 + task number. Gate lịch yêu cầu 45/45 query thực vào solver và 45/45 Python-verified witness trên mỗi bộ. Không đo PUT detection.

Qwen Full164 quét 164 task của cohort. Task không có base-pass hoặc sai cohort size, contract không biểu diễn được hoặc không xác lập được miền input số nguyên được ghi skip có lý do. Dry preflight cho thấy 37 compatible task, 127 skip. Dùng bounds pilot cho 15 task, các task còn lại dùng [-64,64] giao với contract. Qwen `qwen3.5-27b-awq` chỉ viết ba predicate/call, một lần sửa khi JSON hoặc predicate không qua parser, cap 74 logical requests và 222 physical completion attempts tại preflight, 4096 completion / 8192 context và temperature .2. Endpoint profile ngoài repo và ngoài Prefect. Kết quả báo số query, verified target hit, draw, model calls/tokens và fail/skip. Đây là lịch một lần, sau pilot, dùng cùng hai CPU constructors.

### 2026-11-21 — Run 12 task từng bị chặn với Z3 mở rộng

User yêu cầu hỗ trợ số nguyên, chuỗi và list số nguyên rồi chạy Qwen trên subset từ lần Full164 trước. Chọn HumanEval/97,100,102 cho số nguyên, /11,48,54,80,154 cho chuỗi, /26,43,69,73 cho list số nguyên. Các task từng bị chặn theo kiểu, contract hoặc predicate. Cố định [profile và bounds](../../review/z3_unsupported_12_profiles.json) trước run. Chỉ dùng ASCII trong profile chuỗi. Preflight xác nhận trusted contract và bounds của cả 12 task đều dịch được.

Qwen chỉ viết ba predicate/task. Cap 24 logical requests, 72 completion attempts, 4096 completion và 8192 context tokens/request, temperature .2. Z3 và Hypothesis dùng cùng contract và bounds với 3 solver checks tối đa trong 2 giây/task, 250 ms/query, và 64 draw Hypothesis trong 2 giây/task. Predicate qua parser Python nhưng Z3 không hỗ trợ được ghi route Hypothesis-only. Native replay kiểm tra toàn bộ constraint trên witness. Báo số query, target hit theo kiểu input, fallback, call/token và skip. Run này đo witness, không chấm PUT.

### 2026-11-21 — Chạy đủ phần còn lại trong ba nhóm kiểu

User làm rõ cần chạy toàn bộ phần chưa thử. Dùng inventory 120 task số nguyên, chuỗi và list số nguyên. Loại đúng 46 task đã chấm trong hai run Qwen trước, giữ 74 task gồm 3 số nguyên, 42 chuỗi và 29 list số nguyên. Chỉ đo input witness nên không loại task thiếu base-pass PUT. [Profile cố định](../../review/z3_remaining_74_profiles.json) ghi rõ task, bounds, alphabet và provenance của hai run được loại. Một số contract chuỗi có format dùng Hypothesis `from_regex` theo public contract trong profile đã review, để tăng tỷ lệ draw vào domain.

Giữ ba predicate/task, cap 148 logical requests và 444 completion attempts. Các budget thời gian/solver/Hypothesis giữ đúng như run 12 task. Khi contract không compile được, không gọi Z3 trên domain rút gọn. Hypothesis sinh candidate và gửi batch concrete input qua sandbox `validate` với nguyên trusted Python contract, timeout 100 ms/input. Chỉ input được contract chấp nhận mới được tính witness. Khi contract qua parser Python nhưng không biểu diễn được bằng Z3, dùng Hypothesis-only với chính contract đó. Báo target hit, số query đã chạy, native validation, unsupported, budget misses, call/token và skip theo từng kiểu. Không chấm PUT và không sinh input bằng LLM.

### 2026-11-21 — ControlFlow và Z3 trên Full164

User yêu cầu nối Z3 vào ControlFlow và thử full. Chạy một arm opt-in `control_flow_z3` trên HumanEval Full164, 157 task đủ cohort và 1.454 PUT base-pass. Qwen `qwen3.5-27b-awq` dùng endpoint đã xác nhận, max 2 response/task, 314 logical và 942 physical completion attempts. Giữ 4096 completion, 8192 context, temperature .7, 20 input giữ lại mỗi task, 6 target, native trace 1 giây và PUT evaluation 8 giây. Giữ 64 input–PUT observation cho proposal LLM và tối đa 40 Hypothesis draw mỗi task.

Sau khi parse concept, Z3 nhận trusted domain, giới hạn strategy và predicate của concept. Cap 3 query/round, 250 ms/query và 1 giây/round. Witness phải được Python xác nhận trước khi nhập cùng candidate ledger và native trace C1/C2. Các concept chưa dịch được tiếp tục theo đường LLM/Hypothesis sẵn có. Selection ưu tiên input mở rộng target coverage, ưu tiên nguồn Z3-only khi bằng nhau để input đến sau có cơ hội vào cap 20. Giữ provenance qua selection để đếm số query thực, task có SAT, target trace hit, input mới qua oracle và số PUT có failure witness chỉ từ Z3 trong cùng suite. Report tách wrong-value, exception và resource, cùng các task thiếu evidence hoặc skip. Đây là run một arm, chưa có đối chứng ControlFlow độc lập cùng prompt/budget.

### 2026-11-21 — BVA tại guard và contrast cho rule gộp trong DT

User yêu cầu sửa guidance rồi chạy một batch HumanEval Full164 với hai arm độc lập `control_flow` và `decision_table_v2`. ControlFlow chọn giá trị sát ngưỡng sau phép biến đổi, giữ guard trước đó và trusted contract. DT thay một điều kiện được đánh dấu `-` trong cùng rule khi có giả thuyết PUT vẫn đọc điều kiện đó. Review độc lập trước launch xác nhận wiring của hai prompt. Theo review, ví dụ workshop của DT yêu cầu tùy chọn biên nhận không ảnh hưởng đến mọi action của rule, rồi chỉ thay tùy chọn đó.

Qwen `qwen3.5-27b-awq`, context 12.288 theo user, completion tối đa 4.096 token/call, temperature 0,7, tối đa 20 input mỗi task mỗi arm, catalogue bật và PUT timeout 8 giây. Giữ cohort 164 task, 157 đủ điều kiện và 1.454 PUT base-pass. Preview offline dành tối đa 1.456 logical calls cho ControlFlow và 157 cho DT, tổng 1.613 với tối đa 3 completion attempts trên mỗi call. ControlFlow giữ cap 6 target mỗi prompt, 64 lượt trace proposal LLM theo cặp input và PUT mỗi task, tối đa 40 Hypothesis draws mỗi task và 1 giây mỗi lượt trace.

Report trên cùng Prefect run ghi input hợp lệ, PUT disagreement riêng từng arm và union, tiến độ, usage và nguyên nhân skip/fail. Đây là so sánh trong cùng cohort và config. Tác động riêng của từng chỉnh sửa prompt cần đối chứng matched-budget với prompt cũ. Endpoint giữ trong private profile. Theo user, bỏ qua probe endpoint riêng trước launch.

### 2026-11-21 — Qwen Full164 chỉ đổi CF retry

User yêu cầu thử retry mới với batch cũ. Đối chứng là arm `control_flow` đã lưu trên Prefect `8b3acdaa-90bf-4e34-9e18-d3817323a0a0`, với 39 PUT phát hiện. Clone snapshot của arm đối chứng vào output mới và xác minh cohort, runtime, model, prompt vòng đầu và các budget. Runtime chỉ đổi file `arms/control_flow.py`. Giữ visibility, round-robin, cap 6 target và cách trim của batch đầu. Retry ưu tiên target chưa hit, thêm target chưa prompt từ các PUT đã chọn ở batch đầu, cho model xem input hit trong base examples của đúng PUT và dừng khi hết target. Fixture xác nhận prompt đầu giống CF gốc và các hành vi retry.

Một arm, 164 task records, 157 eligible và 1.454 base-pass PUT, 20 input cuối/task, 2 rounds/task, cap 314 logical calls và 942 completion attempts. Giữ Qwen3.5-27B-AWQ, temperature 0,7, context 12.288, completion 4.096, trace 1 giây với 64 cặp input–PUT/task, Hypothesis 32 draw/concept và PUT evaluation 8 giây. Probe endpoint xác nhận model và context. Không nhập model responses hoặc bộ input cũ vào run mới.

Báo số PUT theo wrong-value, exception và timeout, gain/loss theo task/PUT ID so với CF gốc, input hợp lệ, usage và lý do fail/skip. Đọc saved receipts để tính union nếu đủ scope. Hai run sinh model responses độc lập qua các endpoint ở hai thời điểm. Một run được cấp phép, không nối thêm run. Output `final/out/cf_retry_only_qwen_full164_20261121_1vTFfG`.


### 2026-11-22 — Bổ sung target chưa gửi trong CF gốc, ba endpoint

User cho phép chia ba phần chạy trên ba endpoint Qwen. Dùng preparation `cf_original_unselected_targets_prepared_20261122_105737`: 623 target chưa xuất hiện trong request CF gốc `8b3acdaa`, 49 task, 127 batch tối đa 6 target. Chia round-robin theo request đã chuẩn bị, 43/42/42 call. Giữ prompt gốc, Qwen 27B, context 12.288, completion 4.096, temperature 0,7 và seed từ request. Mỗi logical call tối đa 3 physical attempts. Không thêm feedback model call. Endpoint chưa sống chờ tối đa 6 giờ; lỗi và unknown usage ghi theo ledger.

Driver ngoài pipeline gọi bổ sung, dùng parser, Hypothesis, trace, saved-input pipeline và reference hiện có. Phân bổ 40 Hypothesis draws và 64 direct input–PUT trace attempts mỗi task qua các batch, trace timeout 1 giây; giữ tối đa 20 input mới/task ngoài base và input CF gốc. Chấm PUT 8 giây và confirm failure qua evaluator hiện có. Báo riêng extra detections, union với 39 PUT CF gốc, incremental PUT, target hits và usage. Source run/runtime lịch sử giữ nguyên. Worktree pipeline không sửa. Đây là mở rộng budget so với baseline, không phải matched-budget comparison.

2026-11-22 — User yêu cầu cancel run ba shard `a85530d1` rồi chia đôi phần còn thiếu trên hai endpoint. Source đã Cancelled và có 95/127 response, còn 32 request. Continuation copy nguyên request/response/attempt ledger vào output mới, 16/16 request, giữ cap 3 attempts/logical call và toàn bộ config generation/evaluation ở trên. Không gọi lại 95 response đã có.

### 2026-11-23 — Một arm ControlFlow gốc, ẩn static def-use khỏi model

Đối chứng là arm `control_flow` của run Qwen `8b3acdaa-90bf-4e34-9e18-d3817323a0a0` (39/1.454 PUT). Run mới dùng riêng arm này từ cùng snapshot và cohort HumanEval. Prompt đầu và feedback chỉ chuyển `program_id`, `source_sha256`, `coverage_status` từ analysis. Bỏ cụm hướng dẫn dùng static def-use. Giữ source PUT, base input, target C1/C2, CFG path và feedback gốc. Phân tích def-use đầy đủ lưu nội bộ. Model sinh response mới cho run này.

Giữ 164 task, 157 eligible, 1.454 base-pass PUT. Qwen3.5-27B-AWQ, context 12.288, completion tối đa 4.096 token/call, temperature 0,7, seed input/reference 314159/271828. Mỗi task có tối đa 6 target chung cho 2 vòng, 20 input cuối, 64 trace input–PUT, 32 draw Hypothesis/concept và PUT timeout 8 giây. Trần 314 logical calls và 942 completion attempts. Báo gain/loss theo task và PUT ID so với CF gốc, wrong-value/exception/timeout, input hợp lệ, calls/tokens và fail/skip. Hai lượt sinh độc lập. Output `final/out/cf_original_no_static_defuse_qwen_full164_20261123`. Bắt đầu khi người dùng gửi endpoint.

Cập nhật trước launch. Người dùng cấp hai endpoint và yêu cầu chia đôi. Endpoint thứ nhất nhận HumanEval/0–81 (80 task eligible, 755 PUT, cap 160 logical calls). Endpoint thứ hai nhận HumanEval/82–163 (77 task eligible, 699 PUT, cap 154 logical calls). Cả hai phục vụ đúng model với context 12.288. Generation song song, mỗi task chỉ thuộc một shard. Evaluation đọc input đã freeze, dùng chung native lock và ghi lên cùng flow-run ID.

### 2026-11-24 — HumanEval/91, mảng def_use rỗng

User yêu cầu 10 lượt chạy một task trước khi gỡ def-use và c-use. Chạy 5 cặp với cùng seed trong cặp, trên một endpoint Qwen3.5-27B-AWQ. Cấu hình thứ nhất để `"def_use":[]` tại bốn PUT trong prompt, cấu hình thứ hai chỉ bỏ trường này. Cả hai dùng instruction gốc, `data_flow_status=unsupported`, cùng sáu đích C1/C2, chín PUT base-pass, cùng feedback protocol và oracle. Seed model vòng đầu lần lượt 314250, 314350, 314450, 314550, 314650; vòng sau cộng một. Giữ nguyên seed nội bộ, đảo thứ tự điều kiện giữa các cặp. Tối đa hai vòng, 20 input/lượt, 4.096 completion/12.288 context, 0,7 temperature, 8 giây/input, tổng 20 logical calls/60 completion attempts.

Đo chính theo lượt chạy task: trong danh sách input do model đề xuất có chuỗi với ít nhất một câu chỉ chứa từ `I` (tách theo `.`, `?`, `!` rồi bỏ khoảng trắng hai đầu). Ghi riêng chuỗi đúng `"I"`, nguồn vòng, tập input được oracle chấp nhận, số PUT có sai khác lặp lại và bao nhiêu cặp thay đổi ở mỗi chiều. Response không đọc được làm metric đề xuất chưa biết nếu các response còn lại chưa có witness. Năm cặp trên một task chỉ đo tín hiệu tại task này.

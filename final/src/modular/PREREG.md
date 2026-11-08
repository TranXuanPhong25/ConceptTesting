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

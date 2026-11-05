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

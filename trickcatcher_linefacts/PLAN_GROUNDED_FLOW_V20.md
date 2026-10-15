# v20 grounded behavior flow — draft for independent audit

2026-10-15. User requires: write a plan, spawn independent subagent audit, resolve that audit, then begin implementation. No implementation or new experiment may precede completion of this review. This is our own LineFacts design, not a paper reproduction. Preserve all frozen v16–v19 pipelines, vendor code and other sessions' files. No MCTS.

## Objective and honest claim boundary

Build an inspectable connection from a candidate spec obligation to a semantic operation in the implementation, a reachable activating input and native execution evidence. A candidate model matching base tests is not a trusted spec, a trace is not a complete CFG proof, and a node-associated discrepancy is not unique causal localization. Detection continues to require the independent shared-reference evaluator after generation freezes.

The first deliverable is a CPU mechanism implementation and report, not another GPU leaderboard. No automatic GPU launch in this initial implementation phase. Later generation gets a separate append-only preregistration after the CPU contract passes. Do not inherit v19's coverage thresholds or choose tasks by canonical outcomes.

## Required explanation record

Every reported instance must contain:

1. `requirement`: exact quote/span and source hash; typed candidate relation; original admissibility D and eligibility E kept separate; partial-output scope; provenance/status (`fixture_spec`, `reviewed_candidate`, `unreviewed`, `contradicted`, `unknown`). Literal quotation is not entailment. Automatically mined/lexically ranked candidates remain unreviewed.
2. `implementation`: typed semantic operation/effect, stable AST/source span, parameters, explicit data/control links on the supported slice; operation type and side-effect/alias scope.
3. `hypothesis`: discrepancy to investigate, model-origin vs implementation-origin, changed relation/operation with exact source/IR binding; generated from the observed operation and obligation, not registry-prefix order. No fabricated reasoning strings.
4. `trigger`: executable predicate under D, property being contrasted, reachability requirements, expected observable relation and scope. Unknown is distinct from false. A partial obligation never invents a full unique output.
5. `witness`: concrete input plus provenance, bounded native trace showing source activation and local before/after effects, final PUT result/exception, candidate relation result, mutation result where applicable. One input is an existential witness, not a universal proof or total mutant equivalence claim.
6. `limitations`: unresolved dependencies, aliases, unmodeled calls/branches, validity uncertainty, alternate explanations, and whether a local effect propagates to an observable output.

The pipeline emits `incomplete`/`unsupported` with the missing link instead of a success card when this chain cannot be checked. All attempted instances and all20 cohort tasks remain in reporting denominators.

## Implementation phases and acceptance gates

### P0 — independent plan audit before edits

Two read-only reviewers: (A) semantics/source/trace correctness and scope, (B) experimental validity and acceptance criteria. Each reports blockers and a concrete counterexample. Root records responses and revisions in this document/audit log. Unresolved blockers prevent implementation. An explicit written resolution is required; no silently lowering a criterion. Reviewer re-check if revisions change a central design assumption.

### P1 — fail-closed foundation in a new folder

Copy v19 foundation to `pipelines/v20_groundedflow/` with provenance/CHANGELOG; create a new explicitly named CPU entrypoint. Disable inherited experiment entrypoints for this version or clearly reject their invocation so stale v19 runners cannot be mistaken for the new method. Keep reusable scoring/helpers intact.

- AST support validation uses an explicit whitelist recursively over the function; reject match/case, try/with/async/generators, recursive/unknown calls and unmodeled statements/effects. Treat comprehensions/lambdas as nested binders; do not conflate bound variables with free dependencies.
- Correct read-modify-write metadata (`x += y` reads x,y and writes x), assignment order, branch/loop edges, break/continue/for-else, and return-to-exit semantics within the supported subset. Unsupported paths do not count as supported merely because unvisited in base traces.
- Separate `cfg_supported`, `semantic_slice_supported`, `trace_checked` and `spec_reviewed`; none implies the others. A complete supported slice needs explicit boundaries for unknown upstream effects.
- No SSA/alias completeness claim. Model a documented immutable/pure subset; any mutable alias risk outside explicitly checked native observations becomes unknown. Do not certify arithmetic bounds or finite-state completeness.

Acceptance: independent expected edge/read/write cases, including both branch outcomes and loop normal exit vs break/continue/else; explicit rejects for unsupported controls/calls; AugAssign regression. Original-native output agreement alone is insufficient to validate the CFG.

### P2 — lift semantic effects and connect evidence

Start with composable concepts over collection multiplicity, order/filter eligibility, and guarded return conditions. Support only operations implemented and checked by the lifter; give exact subset documentation. Examples are design fixtures, not benchmark-specific dispatch:

- sequence → set/set difference → sequence: possible loss of occurrence count/order; distinguish local loss from whether the output later exposes it;
- filter and sort: membership/order relation and preservation of eligible multiplicity;
- scalar guarded early return: explicit guard relation and successor/output effect;
- append/map pairwise subtraction with optional abs: signed/nonnegative difference when a supported loop mapping is recognized. If the loop cannot be summarized and validated, retain concrete source evidence and abstain on a semantic summary.

Use AST/source IDs to associate native execution observations with these semantic operations, not just nearby source lines. Instrumentation must preserve evaluation order, exceptions and object identity within the supported subset; avoid double evaluation of conditions or iterators. Any rewritten/instrumented execution is checked against original native execution on that input. Unsupported instrumentation yields unknown. Log the relevant path/guard and semantic effects, not the entire unrelated trace.

Do not build an unused FSM. The active artifact is an evidence graph with requirement/operation/control/data/trace edges used to construct the displayed explanation. Every displayed edge cites static construction or concrete observation and its scope. Unobserved graph paths cannot be concatenated into feasible execution claims.

Acceptance: native-vs-instrumented checks include aliasing/exception/order probes even where they must force abstention; effect-specific expectations are authored independently of the lifter. Matched positive/negative/cancellation examples: dedup followed by len reveals loss, dedup followed by sum of distinct indicators may not; distinct output is not automatically a spec violation. No local fact may be promoted to a bug report without a checked output relation.

### P3 — requirement alignment, hypotheses and bounded discrimination

- Begin with synthetic reviewed requirement fixtures for mechanism tests. They are explicitly input specifications, not inferred ground truth for real tasks. They do not contribute benchmark coverage/detection.
- Real-task candidates may reuse pre-gold v18 models as unreviewed proposals only. Their lexical/base compatibility is reported, never promoted to semantic truth. A real-task spec needs a separate documented review with quoted scope/preconditions and ambiguity notes before `reviewed_candidate`; no canonical data in that review. Ambiguous/contradictory specs remain unknown.
- Bind multiplicity concepts to actual multiplicity-changing operations; guard hypotheses to actual control nodes, including unnecessary restrictions, not unrelated count-comparison mutations. Generate alternatives compatible with source semantics, and report whether existing base tests already distinguish them.
- Emit executable trigger predicates and look for bounded concrete witnesses using typed structural constructors + seeded bounded enumeration, not a claimed SMT/symbolic engine. Fixed budgets and provenance; exhausting candidates means `not_found_within_budget`, not unsat/equivalent.
- Require D, E, native source activation, candidate-vs-alternative discrimination and an observable final relation before marking the explanation complete. If exact candidate models are unavailable, partial relations/unknown must be retained, not fabricated outputs. Native violation of a candidate remains `candidate_discrepancy`, not confirmed bug.
- For causality, distinguish an intervention changing output from correlation; a repaired variant or semantic alternative is evidence only for that change/input. Do not assume a repair correct, and retain competing hypotheses.

Acceptance: adversarial negatives that share lexical words/base outcomes but disagree with the requirement, domain-vs-eligibility confusion, unreachable branches, masked local effects, wrong bindings, and multiple faults explaining one input. A correct implementation must not emit a complete violation explanation. Conjunction/window logic beyond the implemented DSL is unsupported, with explicit reason; no claim to handle arbitrary90-day predicates.

### P4 — CPU audit and stop/go report

Run the independent fixture matrix and source/trace checks before any real-cohort output inspection. Freeze fixture suite, subset/config, seeds and budgets in a local CPU preregistration before executing it. Fixes after outputs require recorded amendments/new run IDs, preserving failed artifacts; scientific treatment changes use a new folder.

Then run a CPU representation/binding inventory on the same frozen20 dev task IDs. No canonical/gold/reference execution in inventory. Preserve all20; report supported operations, requirement statuses, complete/incomplete chains and reasons, input/PUT execution/time costs. No required coverage percentage; low coverage is a result, not permission to loosen the subset or hand-patch tasks. No task ID/function-name dispatch. Examples149/110/152 already known from design are labeled as such, not validation success on unseen code.

Stop initial implementation here. Root performs a post-implementation code review against this contract and reports remaining limitations. A mechanism gate requires zero known mismatches in supported acceptance cases, correct negatives/abstentions, no empty bindings/constant rationale masquerading as evidence, and at least one complete independently specified positive plus negative example for each claimed concept family. Do not claim universal correctness from passing this finite suite.

### P5 — separately registered GPU comparison, after mechanism readiness

Only then design/freeze GPU scope, prompts, output schema/adapter and budgets. If user asks for that stage or it is separately authorized, compare behavior+connected-concept vs the identical behavior evidence without normative concept/hypothesis; include plain, matched-request placebo, toolinput and witness-only. All arms use the same original admissibility filter and final input selector; no concept-only acceptance gate masquerading as prompt gain.

A trigger check is a mechanism diagnostic, not an extra final filter unique to the treatment. Shared pre-gold discovery pool/evidence/costs are available to the controls; abstract guidance excludes concrete seeds unless a separate seed-matched contrast is registered. If treatment changes the generator/search algorithm, register a separate tool-only/common-generator ablation and attribute gain to the combined system, not LLM reading a concept.

Check exact output adapter compatibility offline first, without repairing frozen scored runs. Model proposal costs, discovery executions, token/requests, retries/cache and evaluation costs all reported. Freeze generation before same saved spec-only reference scoring. Separate property/model false alarms from D_IO. Full denominator and random equal-input subsets, paired effects and K=1 limitations remain mandatory. No held-out runs, paid fallback or paper reimplementation under this plan.

## Files and execution safety

Planning/audit files at project root/analysis; new implementation only in v20 folder after P0 resolves. Secrets/endpoints never persisted. CPU execution in existing isolated workers; bounded literal inputs/event caps/timeouts and clean worker env. No raw PUT execution from a coordinating main process. Never mutate user input objects across comparisons; preserve input alias topology in each deep copy, or abstain if it cannot be preserved. Commit/push only own files to main; memory stays local.

## Audit disposition

Pending independent reviews. This document does not yet authorize implementation to pass P0; root must append the review and revision disposition first.

## P0 resolutions — accepted before implementation, 2026-10-15

Both independent reviewers completed read-only audits (`audit_flow_plan`, `audit_experiment_plan`). Their conditional acceptance requires the following binding revision, which supersedes the broader initial P1–P4 scope above:

- **Initial active mechanism is multiplicity only.** No guard localization, map arithmetic, general filter summary, symbolic execution or complete FSM. Active semantic entrypoint accepts a pure single-function subset: straight-line local assignments/returns, literal/tuple/list/set expressions, primitive arithmetic/comparisons/Boolean/conditional expressions and lambda binders for whitelisted builtin `list`, `set`, `sorted`, `filter`, `len` calls. No loops/comprehensions, methods, mutation, imports, decorators, defaults/annotations, arbitrary calls or additional top-level execution. Expression branches may execute natively; only actual operation events establish activation. The broader CFG helper has independent regression checks and does not expand this active semantic subset.
- Resolve builtin calls by rejecting shadowing in parameters/locals/lambda binders and any other module statements beyond optional docstring and one target function. Unrecognized syntax/call/effect fails closed; no import/execute in coordinator.
- Input transport checks happen BEFORE serialization: literal acyclic trees, no repeated mutable-container identities, exact builtin types. Initial multiplicity domain is a positional tuple containing flat sequences of exact ints/strings; tuple/literal controls for fixtures may be allowed explicitly. Aliases/cycles/nested mutable elements are rejected, not silently copied into a different topology.
- Instrument exact `set` call IDs with paired before/committed-after events, unique occurrence IDs and bounded immutable snapshots. The input is evaluated exactly once; probes return the identical object. A failing operation has no committed after-event. Do not consume lazy iterators while observing. Native/instrumented observable signatures compare status, value/type, post-input state and within-run output/input alias relations; no cross-process object-ID equality.
- Source-data binding uses an explicit backward slice of the return expression through local definitions and AST child edges. A set operation outside that slice cannot explain a returned multiplicity discrepancy. Scalar/unsupported return scopes abstain from sequence-multiplicity explanation. Pure local effects followed by restoration/cancellation cannot become violations merely because set executed.
- `D(args)` is input admissibility. `E(element,args)` selects each eligible element for a partial occurrence-count relation. E is NEVER a gate requiring every input element to be eligible. `mined_valid` is a provenance-tracked uncertain filter, not trusted spec domain. Fixtures use explicit independently authored D/E.
- Separate `complete_evidence`, `native_checked`, `requirement_review_status`, `candidate_output_violation` and `confirmed_bug` (always unset in CPU phase). Complete evidence does not establish candidate-spec truth. Correct-code/no-violation assertions are only for independently specified fixtures. An unreviewed real-task requirement can produce candidate evidence, never a reviewed-grounded or confirmed-bug count.
- Initial hypotheses are local multiplicity-loss associations, not guaranteed repairs or unique causes. Do not rewrite `set→list` inside set difference and assume a valid repair. Preserve competing active operation IDs and bounded scope.
- CPU fixture suite must contain preserve vs unique requirements, dedup vs sorting-only, dead/unused set, restored counts, distinct-count scalar output, untaken conditional expression, nested/two same-line set calls, builtin shadowing, mutation, aliases/cycles, unhashable types and exception/no-commit evidence. Unsupported branch/loop cases abstain, not fake support. First gate is finite contract validation; no coverage threshold and no GPU auto-launch.
- Root records fixture/subset/config before the first v20 run; all failed artifacts are retained and any correction gets an append-only dated amendment/new run ID. Canonical/reference scoring is excluded from the20-task CPU inventory.

Disposition: all reviewer must-fix items are adopted. P0 is complete; implementation may now begin for this narrowed CPU increment. Independent post-implementation audit will verify these adopted requirements before declaring the increment ready. Review record: `analysis/v20_plan_review.md`.

## cpu_v2 pre-output amendment after independent implementation audit

The original cpu_v1 source was frozen and21 design fixtures passed, but both independent post-code reviewers found wrong lexical argument bindings; one found builtin entry-name shadowing/conditional provenance, the other found unrelated ineligible losses could be combined with a final eligible violation. Therefore cpu_v1 is NOT ready; inventory/GPU stopped before execution. Preserve it unchanged.

Correction is a new `v20_groundedflow_checked` folder with fresh preregistration. Lambda scopes are respected; function-name shadowing rejected. Initial active evidence now rejects conditional/Boolean expressions and requires within-run original argument identity plus a transparent collection-value path, not arbitrary static may-flow. Match per-value eligible losses and before/after counts to the final count violation; masked multiplication/key/control effects cannot count. Derived sequence inputs without observed original identity abstain. Unique-spec mode is a negative control, not a deduplication fault hypothesis. Seven reviewer/cancellation regressions added before new outputs. This is a narrower evidential contract, not universal causal proof. Independent reviewers will inspect the corrected code before inventory.

## cpu_v3 bounded-analysis amendment before new outputs

Independent re-audit accepted cpu_v2 evidence semantics but found analyzer RecursionError when already-rejected reassignments/unbound definitions created cyclic slice definitions. Preserve cpu_v2 source/28-fixture outputs; no inventory/GPU there. New copy `v20_groundedflow_bounded`: reject invalid sources before slicing, visited-definition guard, four regression fixtures and one helper test. Same narrow contract;32 fixtures and13 static checks before inventory, contingent on both reviewers checking the bounded fix. No scope broadening.

## cpu_v4 size/depth pre-output correction

cpu_v3 passed32 authored fixtures but second independent reviewer found oversized AST recursion before deferred size rejection. Preserve source/output; no inventory. New `v20_groundedflow_strict` copy rejects source length before parse, catches parse recursion, and iteratively bounds AST size/depth before recursive helpers. Add size/depth/parse regression and oversize fixture (33 fixtures/14 helper checks). Same evidence scope. This is an engineering fail-closed correction, not a relaxed mechanism gate. Independent recheck still precedes inventory.

## cpu_v5 validator integration amendment before new outputs

cpu_v4 passed33 fixtures and both reviews; actual20 inventory has1 source-supported task, but12 attempts unresolved because direct predicate call used tracer.call's pair convention. Preserve this failed integration result. New `v20_groundedflow_domainfix` calls `valid(*args)` without changing the frozen predicate or admissibility rules; add native accept/reject integration fixtures and worker reason reporting.35 fixtures/14 static checks, same narrow source/evidence scope. Fresh all20 inventory after review/gate; no GPU.

## Current completion checkpoint

P0 audited before implementation. Narrowed P1–P4 CPU increment completed in `pipelines/v20_groundedflow_domainfix`, after preserved corrections and independent rechecks.14 static checks/35 authored fixtures pass. All20 inventory:1 supported known design task,3 complete unreviewed candidate evidence instances,0 reviewed real-task instances. This is not a claim of general abstraction/detection gain. No GPU/D_IO/P5. See analysis/v20_plan_review.md and analysis/v20_cpu_results.md. Broader guards/loops, derived collection provenance and trustworthy requirement inference remain open, to be separately scoped/audited before extension.

## User direction correction — Qwen prompt chaining, 2026-10-15

User rejects static property/effect matching as the main alignment mechanism. Next direction is Qwen extracting concepts, abstracting actual code behavior and identifying candidate mismatches in chained prompts; tools supply evidence and executable verification. The v20 CPU code is a narrow verification prototype, not the chosen semantic extractor. See PLAN_QWEN_REASONING_CHAIN.md. Audit the new chain plan before a new pipeline implementation; no new GPU run from this correction.

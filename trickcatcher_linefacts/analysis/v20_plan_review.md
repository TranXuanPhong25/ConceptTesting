# v20 independent plan review — 2026-10-15

User explicitly requested plan → subagent audit → implementation. Plan existed before spawning reviewers. No pipeline implementation or experiment preceded their final findings.

Reviewers: `audit_flow_plan` (semantics/feasibility), `audit_experiment_plan` (requirements/evidence/fairness). Both were read-only; no API calls, file edits or experiments.

| Must-fix finding | Adopted resolution |
|---|---|
| Broad initial scope repeats v19 ambiguity | Multiplicity-only active mechanism; guards/map/FSM deferred. Explicit accepted/rejected AST/types. |
| Builtin names may be shadowed; module execution unsafe | Single undecorated target function, no defaults/annotations/top-level execution; reject shadowing. |
| Line activation does not identify an operation | Operation-ID + occurrence-ID before/committed-after evidence, once-only evaluation. |
| repr transport loses aliases/cycles | Validate identity topology before serialization; reject unsupported graphs. |
| Equal return values can mask semantic changes | Compare status/type/value, post-input state and within-run return alias signature. |
| Exceptions are not committed effects | Exceptional terminal separate; no after-event when operation fails. |
| Local loss may be unused or canceled | Return backward slice plus observed output property; positive and negative/cancellation fixtures. |
| D/E confusion | D input-domain predicate; E per-element eligibility, not a universal input gate. |
| Complete chain could promote an incorrect spec | Independent statuses; real candidates remain unreviewed, no CPU confirmed bugs. |
| A mutation need not be a valid repair | Local association/discrimination only; no automatic set→list repair of compound expressions. |
| Fixture gain mistaken for benchmark gain | Fixture-only validation, all20 inventory without canonical, known-dev labels, no GPU after coverage. |

Both reviewers conditionally accepted a narrowed design if these items were written before code. Root accepted all and appended the binding P0 resolution to PLAN_GROUNDED_FLOW_V20.md. No unresolved plan blocker remains for the CPU increment; implementation correctness still needs independent checks and post-implementation review.

## Post-implementation audits and preserved revisions

- cpu_v1 `v20_groundedflow`:8 static/helper checks and21 authored fixture expectations passed. Both independent reviewers rejected readiness: lambda-bound names attached to outer arguments, builtin-shadowed entry accepted, static may-flow mistaken for actual argument provenance, and arbitrary local loss combined with unrelated eligible output violations. No inventory/GPU; original protocol/output preserved.
- cpu_v2 `v20_groundedflow_checked`: scoped binding, original-object identity, per-value eligibility/count matching and transparent return transports; conditional/Boolean provenance outside subset.12 helper/28 fixture checks passed. Review accepted evidence semantics but found coordinator RecursionError on already-rejected cyclic/reassigned definitions. No inventory/GPU; source/output preserved.
- cpu_v3 `v20_groundedflow_bounded`: early validation rejection before derived slicing and visited-name guard;13 helper/32 fixtures passed. One reviewer accepted; the other found oversized AST recursing before deferred size rejection. No inventory/GPU; original preserved.
- cpu_v4 `v20_groundedflow_strict`: source length/parse failure handling and iterative AST size/depth rejection before recursive helpers;14 helper/33 fixtures passed. Experiment reviewer statically rechecked oversized/deep/cyclic/normal cases and accepted CPU inventory conditionally on actual33-fixture pass. Same evidence semantics, no general/GPU approval. Semantics reviewer final recheck pending at time of this entry.

Passing the authored fixture matrix did not override independent counterexamples. Each blocker prevented inventory; each correction used a new folder/preregistration before outputs. Scope was narrowed explicitly, never silently widened or relaxed to meet coverage. These are implementation checks on known design cases, not detection gain or unseen validation.

Final disposition before inventory: semantics reviewer also accepted cpu_v4 after independent static rechecks. Actual frozen33/33 fixture gate verified,14 helper tests pass. Both reviewers approve ONLY the full20 CPU inventory under the narrowed contract; no unresolved known blocker for that step. Inventory starts after this entry. No approval/claim of general correctness or GPU readiness.

cpu_v4 actual inventory: all20 retained,1 source-supported task149; all12 attempts unresolved due direct validator signature mismatch,0 complete evidence. This integration failure is preserved; fixture success was not called real-cohort success.

cpu_v5 `v20_groundedflow_domainfix`: only validator invocation corrected to original positional arguments plus accepted/rejected native integration fixtures and worker reason counters. Both independent reviewers checked actual preconditions/tracer/v4_worker conventions and accepted this correction without a scope change; evidence engine byte-identical cpu_v4. Actual frozen35/35 fixture gate and14 helper tests pass. Both approve fresh all20 CPU inventory; no GPU/D_IO/general-correctness approval.

Final cpu_v5 inventory completed unchanged: all20 known dev retained;1/20 source-supported (known design task149),12 native-checked attempts,3 complete candidate count-loss instances,0 reviewed-grounded real-task instances. No unresolved workers remain in the final inventory. No canonical/reference/model API/GPU/D_IO. Final protocol and all preserved prior protocols reverified. See v20_cpu_results.md/json. This completes the narrowed CPU deliverable; broader guard/loop/spec-inference work is not implicitly marked complete.

# CHANGELOG

## 2026-11-04 — injectable input generator and explicit validation blocks

- User requests removing initial concept stages from the main flow and making
  input generation injectable. Core now depends on `InputGenerator`; methods or
  input-producing stages compose through `MethodInputGenerator` without requiring
  ExperimentArm inheritance, concept packets or a model backend.
- Default method is now plain. Modern plain/boundary use lightweight eligibility/
  visibility preparation; core no longer imports/constructs concept or witness
  stages. Original generation steps remain in an explicit legacy adapter for
  archived experiments; CLI requires --legacy-generation for those methods.
- Shared output contract validates task/method batches and literals before
  checkpoint/freeze. Reference/oracle/evaluation consume the same named batches
  from every generator. Manifest freezes generator source/config; read-only replay
  never invokes a producer on a missing checkpoint.
- Extract selection/generation response validation, per-input validation and task
  signature validation into named functions. Mark validation call sites/API/
  context/cache/reference checks with VALIDATION START / VALIDATION END comments.
- Full regression93checks pass, including8new injection tests: independent producer,
  ordinary input stage, no-model/no-packet flow, invalid output rejection, config
  invalidation, default no-concept flow, checkpoint/replay and all-task freeze.
- No live model or cohort benchmark, source-copying, commit or push.

## 2026-11-04 — integrate boundary into the main modular pipeline

- Add opt-in `BoundaryArm` / `--arms boundary`, keeping default arms unchanged.
  Split the existing task input budget equally across template-eligible visible
  PUTs; fixed shares, no fallback or redistribution; deduplicate merged inputs.
- Reuse generation freeze, trusted contract/reference oracle, PUT evaluation and
  existing caches. Report boundary task/PUT statuses and logical selection/input
  calls through generic arm summary hooks, compatible with V11 reporting.
- Boundary-only generation bypasses shared prompts, CFG/DFG analysis and witness
  sampling. Empty suites do not execute reference/PUT code; arm skip survives
  evaluation. Existing arm prompts and historical replay stay covered by regression.
- Add explicit CLI task subset, target-program count and task input budget flags
  so the saved1PUT/task smoke cohort can run through the main entry point.
- Validation:11new integration checks; full modular suite85pass. Only synthetic
  fixtures and their sandbox executions; no live model/cohort benchmark or commit.

## 2026-11-04 — BoundaryValueAnalysis module

- Implement user-requested per-PUT flow in `boundary_value_analysis/`: input type
  extraction → reusable templates → LLM boundary/domain selection → LLM inputs.
- Source types from saved input calls plus PUT/task annotations without executing
  PUTs. Support scalar, length, numeric elements and sum; relational thresholds
  may reference another input value/length/sum. Preserve type provenance.
- Explicit no-template/no-boundary/unsupported/invalid/no-input statuses; no plain
  fallback. Two logical LLM calls maximum, configured budgets and prompt limits.
- Check quote presence, schema, literals, signatures, exact declared boundary
  targets and duplicate inputs. Prose constraints remain explicitly unverified;
  external contract/reference validation is still required before scoring.
- Immutable input/source/config/model identities, per-PUT lock, stage checkpoints,
  transport-error propagation and read-only replay. Existing ModelCalls transport
  and artifact store reused; no registration as a default benchmark arm.
- Validation:41engineering checks pass; offline type/template extraction succeeds
  on all6saved boundary-smoke PUTs with0rejected observations. No real LLM/PUT/
  reference calls, no detection results, no commit/push.

## 2026-11-04 — prospective resource exclusions requested by user

- Audit181remaining PUTs,exclude17source-bound likely resource-heavy programs
  from preparation, BOTH generation prompts and evaluation, as explicitly selected
  by user. Keep source cohort/checkpoints; log effective denominators and task160
  all-base-pass exclusion. No outcome-based selection or retroactive result edits.
- Add optional `--v11-resource-exclusions`, immutable per-task markers and plan
  source/spec/cohort integrity checks. Existing source folder and protocol amendment.
-18targeted checks pass (11existing+7new); full regression/review before resume.
  No commit/push requested.

## 2026-11-03 — user authorizes grouped commits

- User reviewed the change categories and explicitly requested separate commits.
  Source, tests, reports and protocol notes may now be committed on main.
- Checkpoints, runtime outputs, virtual environments and detailed development
  inventory stay local/ignored. No benchmark source or running configuration changes.

## 2026-11-01 — V11 concepts with the existing modern test generator

- User changes workflow: modify existing source in place; no new version folder,
  no commit/push before user review. Separate output data for distinct protocols.
- Add `V11ConceptArm` and `V11ConceptStage` to this existing modular pipeline.
  Reuse original V11 mining/facts/top3/spec fallback only, without the full V11
  hybrid/assertion/expected-output generator. Inherit modern one-call/task
  inputs-only generation, prompt, parsing, reference oracle and PUT evaluation.
- Reuse verified upstream concept caches; missing caches run mining/facts only.
  Selected guidance excludes witnesses, tool inputs and mutant source. Rank-first
  round-robin over visible owners,4cards max, translated AST source locations.
- Track preparation progress/cost independently and compare with plain using
  the existing matched-valid-input method. Preserve modern shortfall exclusions.
- Old full V11 run stopped at user request:288durable case results,4533completed
  result/response/concept artifacts verified unchanged; no automatic resume.
- Validation:26engineering checks pass; upstream-cache check imports525cards from
  264PUTs/28tasks without inference/scoring. Default164task/2296event replay matches;
  original23snapshot hashes and4533stopped-run artifact hashes unchanged.
- Status: implemented, awaiting user review; no new inference or benchmark outcomes
  for this arm, no automatic launch, no commit/push.

## 2026-11-01 — class/module refactor

- Source: equivalent orchestration split from completed concept_reference_v1_recovery;
  existing experiments and artifacts preserved. Shared tested low-level libraries.
- Separate six run types in arms/ and each pipeline stage in stages/.
- Explicit TaskContext, ArtifactStore, ModelCalls adapter and stage dependency order.
- BenchmarkPipeline supports stage insertion and an all-task generation/oracle barrier.
- Default CLI is read-only replay of the completed run; no model construction.
- Validation:15engineering checks pass; independent review cleared. Full164task
  read-only replay/2296events matches inputs/outcomes/full historical summary.
  Original23source/cohort/result hashes unchanged; no new model/native benchmark run.
- Added writable stage_events.jsonl, optional CLI arm selection, witness-only mode
  without a model and configuration-aware cache invalidation.
- Status: complete, remains uncommitted; see VALIDATION.md and README.md.

## 2026-11-02 — remove redundant source copy

- User requests removing redundant code. Removed obsolete `final/v11_clean/`,
  superseded by runtimefix; no active module imports it.
- Keep `final/v11_clean_runtimefix/`: modern concept-only arm imports its mining,
  facts, view, model and sandbox adapters; source hashes remain unchanged.
- Preserve original V11 paper/history sources and every output/checkpoint.
  Active concept-inputs run continues; no commit/push.

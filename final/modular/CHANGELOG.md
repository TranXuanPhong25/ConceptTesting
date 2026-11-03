# CHANGELOG

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

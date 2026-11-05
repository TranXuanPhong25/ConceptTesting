---
name: runtime-refactor
description: Current plain/BVA pipeline uses standalone runtime; obsolete concept arms and adapter removed at user request
metadata:
  type: project
---

2026-11-05 user requests refactoring names and discarding old concept functionality.
Active `final/src/modular` now supports plain/BVA only. Shared executor/worker/contracts,
model transport/checkpoint and keepalive live in `final/src/runtime`; standalone
modular dataset/cohort helpers remove historical runtime imports. Deleted obsolete
concept/V11/classical/contrastive/placebo/toolinput/witness arms, preparation/report
stages, adapter and CLI options from the active package.

Names: `InputGenerationMethod`, `RecordedModelCalls`, `CheckpointedModelClient`,
optional `guidance_id`. Exact frozen-input rescore retains old records unchanged.
Protocol `input-generation-benchmark-v2` requires a current manifest on replay.
Runtime source/executor identity changes can cause cold shared-cache entries;
never weaken identity checks or migrate historical results to force reuse.

2026-11-05 subsequent user approval: delete retired concept code and consolidate
under **final/src** and **final/data**. All current modules now import via `final.src.*`; audit programs moved to src/audits. Removed
41 executable files from concept_reference_v1/recovery/old V11 directories; keep
historical docs and output/checkpoint files, recover original source through Git.

Development grouping now uses neutral cohort/dataset helpers; labels/inventory/
subsets live in final/data/development_groups. Archive holds pre-layout snapshots.
Offline rebuild changed only builder_sha256; all structural evidence and task/PUT
selections identical. Runtime/reference/domain/fixture data paths updated.

214engineeringtests pass;153397recordedoutput/checkpointhashes unchanged. No remote
model calls/new benchmark. Independent layout review completed; output path fixes
keep baseline/audit results under final/out and final/review, never src. See
final/review/src_layout_cleanup_2026-11-05.md and final/README.md. User requests commit/push on main using Conventional Commits without attribution.

2026-11-05 user requests removing excess files. Removed31retired/duplicate files:
old concept docs/locks, original baseline executor/pipeline/CLI, old validation
traces and redundant inventory snapshots (recoverable from Git d1488cb9). Kept
current source/data, research/papers, reports and all final/out checkpoints.
Only writer prompt remains in modular/program_prompts.py; use shared runtime
contracts. Baseline safety tests now target current runtime;2obsolete workflow
tests removed.212tests pass;independent review no must-fix. User requested committing and pushing this cleanup on main without attribution.

**Why:** current reference execution must have clear ownership instead of importing
shared helpers from an experiment whose folder name suggests obsolete concepts.
**How to apply:** trace reference/PUT execution via `final/src/runtime/execution.py`
and `worker.py`; new current methods must not depend on old research packages.

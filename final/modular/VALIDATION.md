# Validation — 2026-11-01

- **15 engineering checks passed**: first14fixture tests, then a targeted15th check
  for the toolinput-only context-budget edge. Independent review reproduced14 and
  inspected the final targeted fix; no remaining architecture/safety blocker.
- Tests cover exact arm prompts, input parsing, standalone writer/base-filter parity,
  full outcome/statistics/accounting parity, cache identity, safe read-only failure,
  stage insertion/dependency rejection, custom arm config drift, zero-model witnesses,
  task-definition drift and the all-task input-generation/oracle barrier.
- Default CLI `final/.venv/bin/python -m final.modular.run` completed read-only replay
  of **all164tasks /2296stage events**. Every reconstructed input/oracle/result JSON
  equals its historical artifact; **the complete summary matches**, including all
  comparison rows, p-values, valid input counts, usage and rejection diagnostics.
- Same raw totals:plain78,classical74,contrastive78,placebo86,toolinput140,witness53.
  This is equivalence validation, not a new benchmark or evidence of concept gain.
- Replay constructed no live model, called no API, and did not execute native PUTs.
  Engineering fixtures separately use the sandbox on tiny synthetic programs.
- Hash verification passed for23original experiment source/cohort/summary/freeze
  files recorded before implementation. Original v1/recovery source, PUT cohort
  and completed results remain unchanged. Snapshot lives in ignored
  `final/out/modular_validation/original_hashes.json`.
- New runtime code has no1–2character local binding names. Syntax compilation and
  diff whitespace checks pass. Source remains uncommitted per user instruction.

## 2026-11-02 — V11 concept-only arm

- **26 engineering checks passed**: the original15 plus11new checks. New checks
  cover one modern inputs-only generation call, exact shared settings/seed/common
  prompt, witness/mutant/reference exclusion, immutable imports, wrong PUT/spec/
  model/source rejection, cache-only/read-only execution bans, mining/facts-only
  dispatch, location translation, visible-owner selection, dependency order,
  checkpoint reuse and propagation of model/cache/CPU-idle infrastructure failures.
- A read-only upstream-cache integration check imported **525selected V11 cards
  from264PUTs/28complete task caches**, without inference, native work or scoring.
  All selected locations with a method line mapped to raw source in that sample.
- Historical **164task/2296stage-event** replay still reconstructs the full saved
  summary. This validates the default six-arm behavior; it is not a benchmark
  result for the new arm. Default CLI remains read-only replay.
- All23original snapshot hashes and4533completed artifacts from the user-stopped
  full-V11 run remain unchanged. That service is inactive/MainPID0, with STOP marker
  and user_stopped statuses;288durable results remain available as checkpoints.
- No model request, new benchmark input suite or outcome was produced for the
  new arm. No independent review of this new arm or efficacy claim is asserted.
  Changes are local and uncommitted for user review; no automatic launch.

## 2026-11-04 — explicit resource exclusions

56combined checks pass:26modular+14native-runtime+9development-selection+7new
exclusion checks. New checks cover source/spec/cohort/plan integrity,early
filtering before prompts/preparation,all-excludedtaskskip,denominator reduction,
consistent evaluation membership,immutable resume markers and refusal of
retroactive exclusions. Independent read-only review found no blocker.

Audited manifest amendment preserved19514existing artifact hashes and the
original manifest/source snapshots.17PUTs excluded with explicit user selection
from preparation,prompts and evaluation;source cohort unchanged. No new model
completion,reference evaluation or native PUT execution during this amendment.
Both available endpoint histories currently return404;resume readiness is saved.

## 2026-11-04 — BoundaryValueAnalysis module

41engineering checks pass using scripted LLM responses: type provenance and
no-code-execution extraction,0/1/2call paths,strict boundary schema/source quotes,
invalid/truncated responses,relational and adjacent-float targets,literal parsing,
signature binding,duplicate filtering,input budget,transport resume,source/model/
config identity,read-only replay and concurrent-controller lock.

Offline extraction on the existing6PUT boundary smoke cohort succeeded for
HumanEval0,18,81,99,120,5 (PUT0each),with0rejected observations. Candidate counts
4/2/3/1/4/4,respectively. This only verifies extraction/template plumbing; it does
not measure semantic selection,input generation quality or bug detection.
No live model call,native PUT execution,reference outcome or benchmark launch.

## 2026-11-04 — boundary integration into BenchmarkPipeline

Full `final/modular/tests` suite: **85 passed** (60.93s), including41module checks,
11new integration checks and existing modular/V11/resource-exclusion checks.

New checks exercise opt-in registration,V11 reporting composition,fixed task-budget
allocation,unsupported/no-template/no-boundary/budget skip paths,cross-PUT duplicate
filtering,avoidance of unrelated graph/witness work,CLI subset/settings plumbing,
generation freeze,real sandbox reference/PUT evaluation on tiny synthetic programs,
two-call accounting,plain+boundary coexistence,checkpoint reuse and read-only replay.
Empty suites demonstrably execute no reference/PUT code. Existing default prompt
and historical fixture replay tests pass. No live model or real cohort benchmark.

## 2026-11-04 — input-generator dependency inversion

Full modular suite: **93 passed** (62.88s). Eight new checks verify the modern
default flow has no concept/witness work, direct injected generation requires no
arm/packet/model, an ordinary PipelineStage can produce an input batch, malformed
outputs are rejected before input checkpoint/freeze/reference, generator config
drift fails before execution, and every task generates before any reference runs.
Cache resume/replay and prior boundary integration/legacy parity checks pass.

Validation code is now named methods with START/END blocks at call sites. No
validation policy was disabled. Only engineering fixtures and tiny synthetic
sandbox programs were executed; no live model or real-cohort result computation.

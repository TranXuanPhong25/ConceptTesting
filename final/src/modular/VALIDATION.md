# Validation — 2026-11-01

## 2026-11-05 — redundant-file cleanup

**212 tests pass** (15.79s). The prior214included2tests for the removed baseline
workflow; its parser/sandbox safety tests now exercise the current runtime.
Independent review:26targeted tests pass,no dangling imports,writer prompt AST
unchanged,contract helper bytes unchanged,and runtime/prompt sources still hashed.
Reports and final/out checkpoints are retained.


## 2026-11-05 — src/data consolidation and concept-code retirement

**214 tests pass** (18.00s), including original baseline, modular/runtime and
development grouping. All task records and task/PUT selections survive offline
inventory rebuild unchanged; only builder source hash changes. 153,397 recorded
output/checkpoint hashes match (0 changes). See
[layout review](../../review/src_layout_cleanup_2026-11-05.md).


## 2026-11-05 — standalone runtime and obsolete-method removal

**197 tests pass** (14.70s):188 current modular/runtime checks and9 development
selection checks. `git diff --check` passes.

The current plain/BVA pipeline imports its executor and recorded transport from
`final/src/runtime`. Sandbox execution.py/worker.py/contracts.py match the earlier
implementations byte-for-byte. A subprocess import test blocks historical research
packages, final.src.pipeline and final.src.run while importing current modules. CLI help
exposes only plain/boundary. Transport/retry tests now target the extracted client.

Independent read-only review verified sandbox parity and dependency removal. Its
missing-manifest replay finding is fixed: current protocol and manifest are now
required, with no-execution regression tests. Existing run data is untouched;
engineering fixtures perform no remote model calls or new benchmark comparison.


## 2026-11-05 — numeric strings and fixed-format boundaries

**205 checks pass** (69.98s): 196 modular plus 9 development-selection checks.
The 40 new cases cover finite numeric-string parsing, float bit preservation,
unrepresentable integer thresholds, public projection evidence, fixed-mask
derivations, parameter binding and behavior/domain separation. An integration
fixture uses the saved PUTs for 99/124 with scripted selection/context responses,
injected generation, global freeze and corrected references in two stability runs.
It confirms construction/integration, not fresh LLM selection or efficacy.
Offline extraction succeeds for all 44 tasks; 1,375 prior run artifacts remain
unchanged. No new model comparison. See the string repair report in final/review/.

## 2026-11-05 — BVA repair

**165 checks pass** (67.68s):modular plus development-selection suite,including
34new regression cases from the saved failure classes. Named argument encoding,
exact float targets,run-length/range binding,domain-role checks,relational guards,
nested shapes,base/obligation budgets,opaque constraints and replay are covered.
Offline old49proposal recheck:43structural passes,6blocked roles/operators;not
semantic precision. Original1336benchmark artifact hashes still match. No new
real model/benchmark run. See final/review/boundary_repair_2026-11-05.md.

- **15 engineering checks passed**: first14fixture tests, then a targeted15th check
  for the toolinput-only context-budget edge. Independent review reproduced14 and
  inspected the final targeted fix; no remaining architecture/safety blocker.
- Tests cover exact arm prompts, input parsing, standalone writer/base-filter parity,
  full outcome/statistics/accounting parity, cache identity, safe read-only failure,
  stage insertion/dependency rejection, custom arm config drift, zero-model witnesses,
  task-definition drift and the all-task input-generation/oracle barrier.
- Default CLI `final/.venv/bin/python -m final.src.modular.run` completed read-only replay
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

## 2026-11-05 — corrected reference programs and frozen-input rescoring

Fullmodular122checks pass (66.30s),including10new checks:164spec/domainbindings
and compilation,97/140corrected outputs,115import relocation,explicit synthetic
references,no silent spec/contract/tolerance fallback,reference-file drift,
exact frozen-input reuse/tamper rejection,separate output,0model calls and replay.

Live44taskrescore completed with no model backend. Validinputs595/121unchanged;
detections3/3→0/0under corrected references. Old1336artifactfiles unchanged,
44generationfreeze identical,118source/datahashes match. Fullread-only summary
replay passes with native/model execution forbidden. Cache1412hits/1766executions.

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

Full `final/src/modular/tests` suite: **85 passed** (60.93s), including41module checks,
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

## 2026-11-05 — shared per-input execution cache

Full modular suite: **112 passed** (63.66s), including19new cache checks.
Coverage includes per-input/repeat reuse,cross-run reference/PUT reuse,independent
stability slots,source/spec/contract/seed/timeout/tolerance/expected/runtime
invalidation,typed values and signed zero,dict insertion order,concurrent callers,
corruption repair,uncached timeouts,read-only refusal and real sandbox isolation
against imported-module state mutation. Existing modern and legacy checks pass.

Small synthetic timing check (8integer inputs,same pinned Python3.11sandbox):
cold0.5399seconds/8executions;warm0.0115seconds/8hits/0executions;outputs exactly
equal. This measures repeated fixture execution,not LLM generation or end-to-end
benchmark speedup. No benchmark outcomes were used to design/cache these checks.

Authorized live smoke subsequently completed6/6tasks:plain80validinputs/BVA19,
0additional PUTfailures each;16responses/0unknown/0retries. Cold-cache432records/
428executions/4hits. A postrun warm-cache audit forbidding subprocess creation
reused all432records,0native/modelcalls,exact equality to original artifacts in
.1202seconds. Fullread-only replay reproduces the complete summary;68source and
6input-freeze hashes verified. See review/boundary_smoke_run_2026-11-05.md.

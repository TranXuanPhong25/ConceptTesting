# CHANGELOG tc_full_v2 (copy of trickcatcher_linefacts/tc_full.py, tc_full_worker.py, generator_worker.py)

Change vs v1 (protocol fix 5, serialisation part): generator_worker.py no longer requires each generated input to
survive a JSON round-trip; inputs travel as repr and are rebuilt with ast.literal_eval (the repr round-trip check is
kept). v1 rejected every tuple input (JSON turns tuples into lists), e.g. task 127 lost 400/400 inputs.
tc_full.py uses this folder's worker via a local generate_candidates (same code as gen_inputs.generate_candidates);
templates, task bundles and outputs stay under trickcatcher_linefacts/ (default out: out/tcfull_v2_qwen7b).
Prompts, sampling, filtering, execution and metrics unchanged.

- 2026-10-14: CPU rerun on the cached v1 generations (no LLM call), out/tcfull_v2_qwen7b. Pools change only for
  task 127 (0 -> 400 inputs) and 157 (300 -> 307, a generator timeout). Still empty: 50, 66, 119, 161, all from
  Qwen-written generator code errors (cyaron API misuse, NameError, wrong arity), faithful to TrickCatcher, not an
  adapter bug. Paper metrics (all 133 tasks): detecting samples 151 -> 154, any-of-K 53 -> 54, FA rate 9.3% -> 10.5%.
- Not done here (left to v11_fair / final protocol): crash/timeout accounting and budget alignment with the other arms;
  ref/full rescoring on dev.
- Status: adopted as the TrickCatcher-full baseline.

## 2026-10-14 — held-out adapter readiness (CPU only)

- `load_tasks` accepts a complete held-out bundle without the HumanEval 133-task gate.
- Initial `final_run.py` / `final_worker.py`: explicit per-sample variant/generator allocation,
  total <=8 logical calls, K=3 independent samples, <=20 distinct assertions in generation order.
  Original `tc_full.py gen/run` retain historical 10-variant/4-generator shared-pool semantics.
- Final mode uses repr/ast.literal_eval input transport and plain wrapper-call assertions
  (container types retained), with the v11_fair_vp tolerant comparator for base filtering/voting.
- Successful variants can report a crashing/timed-out PUT; count PUT and variant failures.
  Generation/filter/vote receive only PUT, spec/docstring and public base tests plus numeric atol.
  No canonical answer, private test, mined validator or reference program enters those stages.
- `--fake` is a local scripted client; default is cache replay; only `--online` reads the endpoint.
- Dry allocation 4+4 was used solely to check the adapter, not as a confirmatory configuration.
  This initial adapter and its pending allocation are superseded by amendment 1 below.
- Verification: 3 VibePass + 3 MBPP+ PUTs, K=3, 18 rows, 8 scripted calls/sample,
  one exported assertion/sample; 5 CPU tests cover crashes, tolerance, container types,
  failed variants and majority-vote ties. See `../tests/heldout_dry/summary.json`.

## 2026-10-14 — registered Final protocol amendment 1

- `final_run.py` now fixes the paper's 10 variants + 4 generators per task, with
  the original request/draw seeds and a single multiplicity-preserving pool.
  All three seeded resamples share that pool. Removed allocation CLI options;
  there is no reduced mode. The historical `tc_full.py` entry remains unchanged
  by this amendment.
- Per-task request budget: 14 <= 3*8 = 24; generation-order distinct assertions
  remain capped at 20/sample. Requests/tokens have one task-level ledger and are
  partitioned round-robin across rows for accounting only (5/5/4), giving 14/3
  mean calls/sample without counting the shared generation three times.
- Shared generation, candidate pool, filtering and generator outputs resume
  from task artifacts. Missing sample results rerun only that CPU resample;
  no additional generation query or candidate draw is needed.
- Every row records shared generation/pool identity, the original resample seed
  and selected pool positions. Shared scorer, wrapper assertions and crash/
  timeout labels remain those of the readiness adapter.
- Seven unit tests pass, including token/call attribution, real request seed
  identity, one shared pool, cap/drop order, partial resume and reduced-mode
  rejection. Fresh offline dry run: 3 VibePass + 3 MBPP+ PUTs, K=3, 18 rows,
  exactly 84 scripted logical requests (14/task), zero model/network requests.
  See `../tests/heldout_dry_amendment1/summary.json`.

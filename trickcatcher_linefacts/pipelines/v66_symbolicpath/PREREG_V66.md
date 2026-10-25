# PREREG v66 (committed as v65; renumbered 2026-10-25 because another session used v65_evidencegate) — CrossHair backend for the v57 source-derived path constructor

Frozen 2026-10-25 before any real-case construction outcome. Engineering readiness only; not a concept-efficacy test.

## Question
v57 built 0 verified solver inputs on all six pilot cases (61, 66, 124, 58, 131, 85) because its own Z3
interpreter lacked nested functions, comprehensions, sets, dicts and nested sequences. Does replacing that interpreter
with the unchanged pinned CrossHair 0.0.112 / Z3 5.3.1.0 (Python 3.12) produce verified reach + local-difference +
output-difference inputs on those real sources?

## Mechanism (frozen)
- Hypotheses: v57 source catalog (`hypotheses.catalog`, cap 48, round-robin), with one source-only fix: annotation
  subscripts (`List[int]`) excluded (definition-time, not runtime sites). No writer proposals, no LLM.
- Original and alternative are instrumented at the exact AST span; symbolic args go through deep copies into both.
  Witness requires normal return of both, first differing site event with equal pre-site state, frame and branch
  prefix (`local_difference`; STATE_ACCUMULATION needs ≥2 visits), and different outputs.
- Store/Del subscript sites: observed value is the selected index.
- Search domain: types from public examples; ints in [-1000, 1000]; top-level sequences ≤6, nested ≤4; strings over
  the public character categories. These are search bounds, not validity rules.
- Every symbolic witness is realized and re-run in an `unshare -rn` CPython worker, instrumented and uninstrumented,
  twice. Counted only if outputs, branches, site events and pre-states match exactly and repeat.
- Exceptions, timeouts, nondeterminism, library errors = unknown, never witnesses; no-witness = bounded, not UNSAT.

## Budget (frozen)
`config.json` `symbolicpath`: ≤400 paths and 20 s per hypothesis, 2 s per path, ≤2 models per hypothesis,
40 s replay per hypothesis. One run, no retries, no budget increase after outcomes.

## Metrics and decision
Per case: catalogued hypotheses, verified hypotheses, distinct verified inputs, status counts, path outcomes.
- PASS (backend ready for integration into the v57 prompt controls): ≥4/6 cases with ≥1 verified hypothesis.
- PARTIAL: 1–3/6 → report blockers per case; no expansion of budget or cohort.
- STOP: 0/6.
Verified inputs are behavioral differences between PUT and a source edit; whether they are valid per spec or reveal
a real bug is unknown and not measured here (no hidden tests opened).

## Out of scope
No model calls, no private oracle/scoring, no v58 comparison. Later efficacy needs its own PREREG.

## Amendment 1 (2026-10-25, after independent Sonnet code review, before any real-case outcome)
Reviewer verdict PASS-with-fixes; no unsound-witness path found. Applied:
- Statuses split: `unknown_library_error`, `unknown_realization`, `unknown_timeout_or_cap` (path cap or time budget hit),
  `bounded_no_witness` only when the bounded search ended on its own; `harness_error` per hypothesis keeps the denominator.
- Opaque (unencoded) outputs are never certified; Counter/OrderedDict/deque/namedtuple encoded by content;
  uncopyable pre-state values become typed markers instead of raising inside the PUT.
- Native replay: two separate worker processes (PYTHONHASHSEED 0 and 65) must agree; native local-difference index must
  equal the symbolic one; RLIMIT_FSIZE/NPROC added; `unshare -rn true` preflight recorded in the manifest and required.
  Isolation is network + resource limits only, not filesystem.
- Worst-case time per case ≈ 48 × (20 s explore + 40 s replay) = 48 min; overruns are logged, not enforced.
- Decision rule unchanged (≥4/6 PASS) but it is a low bar: also reported and interpreted are verified hypotheses by
  family and site kind, and the share of catalogued hypotheses verified per case. A PASS means only "backend constructs
  real-source witnesses", never "useful fault concepts".

## Amendment 2 (2026-10-25, harness crash, before a complete run)
Run 1 (`out/pipelines/v66_symbolicpath_crashedrun1`, was `v65_symbolicpath/cpu6_20261025`) crashed in 5/6 cases while
writing JSON: witness rows built inside the CrossHair callback were CrossHair shell containers (`ShellMutableMap`).
Only case 58 completed (48/48 `unknown_timeout_or_cap`, 0 verified); a partial file showed case 124 had ≥1 verified
row before the crash. Fix: realize under tracing, encode/build rows under `NoTracing`, JSON round-trip; tests assert
plain-JSON reports. No mechanism, catalog, budget or decision change. Full rerun of all six cases (including 58) into a
fresh directory with the same frozen budget; run 1 is kept and not used for the decision.
Renumbered v65→v66 (other session's v65_evidencegate).

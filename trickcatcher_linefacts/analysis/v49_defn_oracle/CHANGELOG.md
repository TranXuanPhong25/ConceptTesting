# v49 oracle implementation — 2026-10-23

Implements the original PREREG with Amendment 1 taking precedence. Generation remains owned by `gen.py`;
this change makes no model/network calls and does not change generation records or imported experiments.

- `oracle.py`: read-only generation status (495 v49 slots and 310 v46 tc slots); strict public-input
  validation at 2 s for every family; v46 loading, typed equality and batch/per-program crash fallback;
  full v48 menu-union plus seeded pool universe at 1 s, in v49-owned execution caches.
- Primary quorum counts every valid program in V, including input-specific timeouts, exceptions and crashes.
  Reports finishing-only quorum, native v46 largest-differing-group voting and v48 unanimity, plus defn∧tc.
  PUT exceptions/timeouts never produce tests. Invalid/overflow tc slots remain in all 252 generated-slot
  k=5 subsets; each subset applies its own validity count and test cap before averaging task/test metrics.
- `score` checks complete generation, complete full execution, execution hashes, program/pick prompt digests,
  the exact input universe and 24 spec hashes before loading any reference. Reuses v48 reference truth,
  judge, cap ordering and task aggregation. New reference/official caches stay under v49; imported v41
  references are read-only. Uses `flow_common.immutable` for `inventory.json` and `score.json`; failures
  write `score_incomplete.json`. Score has **not** been run during implementation.
- Reports decisive and llm_code-only metrics, paired V>=2 comparisons (including subset-conditioned tc_k5),
  uncapped results, common mode, abstentions, resource-only rejections, crashes, finish reasons, comments
  and AST similarity. Decision uses defn vs brute, +3 tasks across >=3 distinct problems, FA no worse;
  secondary brute vs plain uses the same thresholds, and defn vs tc is reported. Defn-only confirmed
  tests carry majority-program IDs and pending manual enumeration/comment-correctness audits; numerical
  GO does not automatically attribute a win to correct concepts.
- `test_v49.py`: reference-free unit/integration checks, including a real isolated worker timeout, exact
  quorum boundaries and typed values, generated-slot subset means against independent brute force,
  subset-conditioned pairing, problem clustering, strict validity, code extraction, SHA cap ordering,
  status/preflight isolation and crash fallback.

Engineering clarifications/extensions (no changes to the registered scientific rules):

- Full `execute` requires complete planned generation. `execute --tasks ...` runs only present records
  and writes an immutable snapshot under `out/analysis/v49_defn_oracle/smoke/<artifact-hash>/`; missing
  records are not invalid programs. These partial results cannot be consumed by full `score`.
- Common mode requires at least one finishing valid program; zero-finishing exposing inputs are reported
  separately. Its share uses all exposing inputs as the denominator.
- Precision, including tc_k5 precision, is confirmed tests / tests after aggregating exact expected counts,
  matching v48 aggregation. Confirmed/FA task indicators themselves are averaged within each subset.
- The required literal entry-function `ast.dump` similarity is retained. VibePass tc modules can inherit
  an identical PUT wrapper, so a separate implementation-function similarity resolves `Solution().method`
  to its method. It is an additional diagnostic, never an oracle or decision gate.
- The original cross-family defn∧tc and native v48 unanimity reports are retained alongside Amendment 1's
  required rules. They do not affect the primary decision. No PREREG scientific deviations.

Initial validation, before the v48 compatibility update (specified Python, `PYTHONPATH=.` and bytecode disabled):

- `pytest -q -p no:cacheprovider .../test_v49.py`: **51 passed** (3.06 s).
- Initial `status` during generation: defn 4/165, brute 4/165, plain 4/165; total 12/495. v46 tc 26/310
  across 31 planned tasks. All present records had finish_reason=stop; length/context_overflow=0.
- Public-only spec check: 33 tasks, 24 distinct spec hashes. Duplicate groups match the preregistration:
  3/96, 39/58, 46/75/77, 61/65/66, 69/70, 73/74/161. Tc has no generated programs planned for 6/103.
- `execute --tasks 3`: snapshot `smoke/cc2fffaa7516d25f`, 991 universe inputs and 3 public inputs;
  PUT normal on all of them. Smoke preceded the final status snapshot: present/valid counts were
  defn 4/4, brute 4/1, plain 3/0, tc 10/8. Rejections: brute mismatch=2 and RecursionError=1;
  plain mismatch=3; tc mismatch=2. Crashed programs=0 in every family. Uncapped primary emissions:
  defn 380, brute/plain/tc 0. These are **unscored** emissions, not confirmed tests or a scientific result.
- Smoke inventory rechecked: all 96 artifact hashes unchanged; no smoke reference files or score output.

No commit/push attempted. No shared-memory or other experiment files edited. Pytest scratch files are
confined to this implementation folder and removed after validation; only the explicitly requested v49
smoke output is written outside this source folder. Counts above are snapshots of ongoing generation.

## v48 API compatibility — 2026-10-23

Updated against coordinator commit `7808afd`, without editing v48 or running score:

- `oracle.py`: the score-only `task_truth` adapter passes all decisive-universe inputs as the fifth
  `diag` argument to v48 `reference_truth`, preserving reach/official exposure for abstention/common-mode
  diagnostics. `exposing=None` remains unknown: it cannot confirm a test and is reported separately
  from evaluated exposure. Skipped references are reported as input/test counts; unconfirmed tests
  still count as FA. Metric aggregation preserves these counts.
- Uses v48 `put_ok` for voting, eligibility, paired comparisons and execution summaries. The summary
  field is now `put_no_test_inputs`, covering exceptions, timeouts, skipped and unparseable PUT outputs.
  Inventory keys and displayed paths use v48 `rel`, including paths outside the repo in unit tests.
- `test_v49.py`: four added regressions check the five-argument adapter with a stub (no real references),
  unknown exposure/skipped-reference diagnostics, renamed metrics and aggregation, and external-path
  inventory keys. **55 tests passed in 3.19 s** on the specified Python.
- Final `status` snapshot: defn 5/165, brute 5/165, plain 4/165; total **14/495**. v46 tc **29/310**.
  Every present record is `stop`; `length=0`, `context_overflow=0`, no bad records. Generation remains incomplete.
- Final `execute --tasks 3`: `smoke/4141bbdac9fb1fb6`; 991 universe inputs and 3 public inputs;
  `put_failed_public=0`, `put_no_test_inputs=0`. Present/valid: defn 5/5, brute 5/2, plain 4/0,
  tc 10/8. Rejections: brute mismatch=2, RecursionError=1; plain mismatch=4; tc mismatch=2.
  No crashed programs. Uncapped primary emissions: defn=380, brute=380, plain=0, tc=0; all are unscored.
  Earlier smoke snapshots are preserved unchanged.

PREREG deviations: none introduced by this compatibility update. The engineering clarifications above
remain unchanged. No real references, model/network calls, generation edits, commits or pushes.

## 2026-10-23 (Claude) — review fixes (PREREG Amendment 2)
Per-problem net span rule (+test), tc extraction via tc_full.source, chunked parallel execution with scaled process
limits, official reach limited to menu ∪ llm_code with lazy checks for emitted tests, defn_vs_tc report-only.
56 tests pass; task-3 smoke re-run (2.8 s): defn 5 valid/380 primary tests, brute 2/380, plain 0, tc 9 valid/0 tests.

## 2026-10-23 (Claude) — next-branch rules before any output
`PLAN_NEXT_v50.md` (draft, not registered): branch rules R1 > R3 > R2 > R5 > R4 fixed before v48/v49 execute/score,
from AutoCode (2510.12803), CodeHacker (2602.20213), DePro (2603.19399), HardTests, B4. `plan_rules.py` evaluates them
after both scores (recomputes the `defn` FA split with v48 semantics; v49 score lacks it); `test_plan_rules.py` 5 synthetic
tests (61 total pass). `oracle.py`/`gen.py` unchanged.

## 2026-10-23 (Claude) — client read timeout 3600 → 900 s (execution detail, no effect on prompts/params/digests)
Twice (04:27, 11:28) a request vanished from the server (running/waiting 0 for v49) while the client held an idle
connection for the full 3600 s. 900 s still exceeds one queued call of the other client plus our own 1024 tokens.
Revision 1 (19:45, after an independent read-only Opus review, before any output): per-task v48 decomposition adapter on
the whole decisive universe (proxy exposure off the official subset), R1 gated on the manual audit, new R1b (near-GO FA)
and R6 (family effect) branches, R3 on valid/resolved tests and problems, R5 on `defn` FA only, score.json consistency
guard, immutable output; v50-V/v50-S/v50-H text fixed (B5/F1b, F4/F4b prior art; no shrink of foreign inputs). 63 tests.

## 2026-10-23 20:30 (Claude) — generation complete 495/495, 0 errors
At 19:30 another session moved the gen to a second idle endpoint (same `served_model_name`, same weights root
`Qwen/Qwen2.5-Coder-32B-Instruct-AWQ`, `max_model_len` 8192; gen.py checks both). 438 programs came from the first
endpoint, the last 57 (tasks 163, 164, 168, 171) from the second; prompts, params and seeds are unchanged.
Execute/score wait for v46 tc (280/310) and v48 (orchestrator, sequential).

## 2026-10-23 23:15 (Claude) — execute + score + plan rules, RESULTS
Primary NO-GO (defn 12 vs brute 10 tasks, margin 2 on 2 problems, FA 145 > 100; paired identical 10/10); secondary
NO-GO on FA only; defn vs tc report margin 11. Manual audit of 103/124 passes. plan_rules: R7 (no exposing input, 8
tasks). Family effect report-only: defn/brute precision ≈ 0.6 and common-mode 3–5% vs tc 0.23 and 28%. See RESULTS.md.

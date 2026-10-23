# v48 end-to-end oracle implementation — 2026-10-22

Implements PREREG.md and Amendment 1 using frozen v47 menus/picks and v46 tc programs. No new model calls,
network research, evaluator reads, or scoring were performed. All source changes are new files in this folder;
engineering outputs are confined to `trickcatcher_linefacts/out/analysis/v48_e2e_oracle/`. PREREG and existing
experiments remain untouched. Shared memory is outside the task's explicit write scope and was only read.

## Files

- `e2e.py`: JSON status; completeness-gated execution; isolated `--tasks` smoke; unchanged v46 batch, wrapping,
  program loading, base validity and fallback semantics; digest checks; singleton-aware typed vote and consensus;
  score-only reference access; artifact inventory; all nine registered arms; exact item controls and seeded
  count-matched controls; capped and uncapped results, both task cohorts, upstream costs and diagnostics.
- `menu_fixed.py`: tool-only rebuild; integer `**`/`^` and `len()` bounds; explicit unsupported-constraint reports;
  per-argument range checks; set dedupe within kinds and across shown menus; negative log-uniform sampling;
  incomplete cases on kind errors/unsupported constraints; prompt-digest checked cache reader; `diff_current33`.
  Coverage and mutation reuse frozen caches read-only; a missing/different coverage cache is a kind error.
- `test_v48.py`: reference-free pytest checks for vote/equality, ordering/caps, exact controls, deterministic
  matching, parser and range fixes, dedupe, negative sampling, cache validation, completeness, diagnostic FA
  categories, inventory changes and output redirection.
- `CHANGELOG.md`: implementation scope, verification and protocol choices.

## Verification and current status

- 44 pytest cases pass with the requested Python and `PYTHONPATH` set to the repo root. Persisted votes use
  worker repr outcomes and are reparsed with `iorel.value`; JSON round trips preserve v46 typed equality,
  including `None`, bytes, nested containers and float tolerance.
- Task 3 smoke: 991 distinct inputs, 9 valid programs out of 10, 202 uncapped vote emissions, 0 consensus
  emissions, 0 PUT exception/timeout inputs. A repeated smoke verifies cache reuse and identical results.
  Smoke artifacts live under `smoke/<e2e-source-sha256-prefix>/`, never the main execution directory.
- Status snapshot during implementation: v47 60/66 planned call records; v46 tc 20/310 planned program records;
  33 tasks, 31 with planned programs; tasks 6 and 103 abstain; 0 observed context-overflow records. Upstream
  sessions are still writing, so these counts are a timestamped observation, not a frozen result. Full JSON:
  `out/analysis/v48_e2e_oracle/status.json` (relative to `trickcatcher_linefacts/`).
- The final status check observed 62/66 calls and 22/310 programs; the main `execute` command correctly
  refused incomplete inputs (exit 1), before creating any main execution cache.
- All 59 v47 calls present at the prompt audit matched their reconstructed prompt digests; task 3's ten tc
  digests also matched. No records were repaired or rewritten.
- `diff_current33`: menu changes only for tasks **39, 58, 73, 74, 161**, matching the audited order duplicates.
  Tasks **39, 58, 103, 124, 171** additionally report unsupported dynamic constraints (`min(...)`, variable
  length bounds, conditional indexed constraints) and are conservatively marked incomplete; no kind builder
  failed. The command exits 1 to expose those incomplete cases. Report: `out/analysis/v48_e2e_oracle/menu_fixed_diff.json`.
- `score` was deliberately not run. No `score.json`, `score_incomplete.json`, reference batch, or official
  evaluator output has been created by this implementation session. Final scoring requires complete upstream
  records and a complete main execution run.

## Protocol choices / deviations

No registered scientific arm, gate, oracle rule, input universe or frozen menu was changed. The following
unspecified engineering details are made explicit:

1. “Exact where small” means `C(N,n) <= 20000`; otherwise 2000 draws without replacement within each draw,
   with replacement between draws. Seeds are `v48/menu_matched/<task>` and `v48/pool_matched/<task>`. Universes
   use the shared sha256 input order. If n exceeds the universe size, scoring is incomplete rather than
   silently reducing n. The pool subset seed remains exactly `v48/pool/<task>`.
2. A menu with fewer than three items uses all available items for random3; empty picks yield the one empty
   kind-matched selection. Neither case repairs a model response.
3. Unsupported dynamic constraint forms are reported and mark only future fixed-menu cases incomplete;
   their dependent bounds are not approximated. Positive-range sampling preserves v47's seeded behavior;
   the sign-aware log-uniform extension applies to negative-containing ranges.
4. Failure flags a–e may overlap. FA splits also expose `unconfirmed_official` and `unresolved_output` rather
   than forcing unavailable evidence into a wrong-value category. Diagnostic input lists are deterministically
   ordered. Both capped and uncapped FA splits are retained.
5. Official scoring caches are local to v48, keeping existing v41 outputs read-only. Execution inventories
   include imported repository source hashes, workers, configuration, templates and every consumed data/cache
   artifact; scoring rejects changed execution inputs before loading evaluator data.

## Git delivery

The checkout is on `main`. Staging exactly the four new files failed before any index change:
`fatal: Unable to create '/home/phong/dev/ConceptTester/.git/index.lock': Read-only file system`.
The session disallows permission escalation, so no commit was created and no push was attempted. No other
session's files were staged. A validated patch of these four files is saved at
`trickcatcher_linefacts/out/analysis/v48_e2e_oracle/implementation.patch` for the writable checkout owner.

## 2026-10-23 (Claude) — review fixes before full execute
Opus code review: must-fix test path independence; should-fix decomposition gaps (PUT no-test, variant failures,
cap loss, totals), official-check scope, no-test counting, reference chunk fallback. Applied in `e2e.py`, test added
(45 pass). PREREG Amendment 2. Full `execute` still waits for v46 `tc` programs (owner session concepttester-ca).

## 2026-10-23 (Claude) — execute + score, RESULTS
v46 tc reached 310/310 at 21:46; execute (rc 0) and score (rc 0, 0 reference skips) ran unattended. NO-GO: llm_code 6
confirmed tasks vs random3 6.37, menu_matched 6.38, pool_matched 5.87, kind_matched 6.22, heuristic 6; FA 152 vs
146.37. Primary failures: common-mode 9, no valid variant 7, no exposing input 7, lost to cap 3. See RESULTS.md.

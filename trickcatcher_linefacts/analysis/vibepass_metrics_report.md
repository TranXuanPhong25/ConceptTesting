# VibePass metrics (arXiv 2603.15921, RQ1) on existing dev runs

Run plan addition (a) in PREREG.md (2026-10-13 ~02:00). CPU only, no LLM call. Script: `analysis/vibepass_metrics.py`.
The full tables (every arm, every oracle, assertion and sample level) are in `out/vibepass_metrics/tables.md`, and the
raw counts, including per-task counts, are in `out/vibepass_metrics/metrics.json`.

Rerun (from the repo root; sandbox results are cached in out/vibepass_metrics/res, so a rerun takes about 1 min):

    python3 -B trickcatcher_linefacts/analysis/vibepass_metrics.py

## Definitions
Unit = a unique call in a sample (repeated calls in a sample are counted once and the first assertion is kept, as in
oracle_b01.score). Dev split only, 113 tasks, K = 3.

- **V_I**: the input satisfies the EvalPlus contract (the `valid` field in the oracle dir's exec/). A call whose
  arguments cannot be evaluated, or that uses keyword arguments, counts as invalid.
- **D_I**: V_I and PUT(x) != canonical(x). This is computed again in the sandbox with the unchanged `analysis/worker.py`
  (`unshare -rn python3 -I -B`, 3 s per call). Floats are compared with tolerance (rel 1e-6, abs = the task's atol or
  1e-6). A PUT exception or timeout counts as different. If the canonical program fails on a valid input, the call is
  not counted in D_I (57 / 51 / 12 / 24 calls in v7 / v8 / evalmitigate / advhyb).
- **V_IO(o)**: V_I and oracle o gives an expected value that equals canonical(x) (`oracle_b01.decide` canon_ok).
  **D_IO(o)**: D_I and the same condition.
  - o0 = the LLM's own assertion. Its expected value counts as correct if the assertion passes on the canonical
    program. o0 never abstains.
  - b1one = only the first sample of the code-hidden B1 prompt.
  - ref = B2 (unanimous Qwen reference programs).
  - full = ref + judge + post. For v8-strict and advhyb there are no judge responses, so full there is ref + post.
- **Per sample**: the sample has at least one such call. The value is the number of such samples divided by K, which
  equals tasks per run. This is the same unit as RESULTS ("ref 67.0").
- **Gaps**: fault-hypothesis (FH) = V_I − D_I; output-validation (OV) = D_I − D_IO(o).
- **Abstention** (share of calls where the oracle gives no expected value, out of all calls): ref 10.5–14.2%,
  full 11.6–15.2%, b1one 0.1–0.5%.

Cross-check: D_IO(ref) per sample matches the existing detection metric. Examples: v7 concept-hybrid 66.7 vs RESULTS
67.0, and v8 concept-hybrid 61.0 vs 61.0. The two differ on at most 44 calls per run, for three reasons:
- float tolerance (task 20);
- a PUT whose output order depends on the string hash seed (task 34);
- PUT timeouts at 3 s that the original evaluation saw pass (task 41). D_I counts these as different, as specified.

The exec `valid` and the worker's contract check agree on every call.

## Per sample (tasks per run, out of 113; advhyb out of 112)

| run | arm | V_I | D_I | D_IO o0 | D_IO b1one | D_IO ref | D_IO full | FH = V_I−D_I | OV o0 | OV ref |
|---|---|---|---|---|---|---|---|---|---|---|
| v7 | toolinput | 110.3 | 75.7 | 47.0 | 52.3 | 64.7 | 65.0 | 34.7 | 28.7 | 11.0 |
| v7 | concept-hybrid | 112.0 | 75.0 | 51.7 | 57.3 | 66.7 | 65.3 | 37.0 | 23.3 | 8.3 |
| v7 | plain-hybrid | 113.0 | 67.0 | 50.7 | 51.0 | 57.3 | 56.3 | 46.0 | 16.3 | 9.7 |
| v7 | concept | 110.0 | 54.7 | 36.0 | 38.3 | 48.0 | 46.3 | 55.3 | 18.7 | 6.7 |
| v7 | placebo-hybrid | 113.0 | 52.3 | 36.7 | 40.7 | 45.7 | 43.3 | 60.7 | 15.7 | 6.7 |
| v7 | plain | 112.7 | 51.7 | 40.3 | 41.3 | 45.0 | 43.3 | 61.0 | 11.3 | 6.7 |
| v7 | gen-plain | 112.7 | 47.3 | 33.0 | 34.7 | 41.3 | 40.3 | 65.3 | 14.3 | 6.0 |
| v8-strict | toolinput | 110.3 | 75.7 | 47.0 | – | 64.7 | 64.0 | 34.7 | 28.7 | 11.0 |
| v8-strict | concept-hybrid | 110.7 | 69.3 | (43.7)* | – | 61.0 | 60.0 | 41.3 | * | 8.3 |
| v8-strict | plain-hybrid | 112.7 | 64.3 | (48.7)* | – | 55.7 | 54.7 | 48.3 | * | 8.7 |
| v8-strict | placebo-hybrid | 113.0 | 52.0 | (36.3)* | – | 45.3 | 43.0 | 61.0 | * | 6.7 |
| evalmitigate | advdoc | 112.3 | 50.0 | 38.7 | 41.3 | 42.7 | 41.0 | 62.3 | 11.3 | 7.3 |
| evalmitigate | onlydoc | 112.7 | 47.7 | 37.7 | 38.7 | 40.3 | 39.7 | 65.0 | 10.0 | 7.3 |
| advhyb (partial) | advdoc-hybrid | 111.3 | 63.0 | 46.7 | – | 56.0 | 54.0 | 48.3 | 16.3 | 7.0 |
| advhyb (partial) | advdoc-plainhybrid | 111.3 | 58.7 | 44.3 | – | 51.3 | 50.3 | 52.7 | 14.3 | 7.3 |

\* v8-strict rebuilt arms carry placeholder expected values, so o0 is not meaningful there. v8-strict copies the arms
concept, plain and gen-plain unchanged from v7. "–" = no b1 responses in that oracle dir.

## Per assertion (% of unique calls)

| run | arm | calls/sample | V_I | D_I | D_IO o0 | D_IO ref | FH (pp) | OV ref (pp) |
|---|---|---|---|---|---|---|---|---|
| v7 | toolinput | 8.7 | 95.3 | 16.6 | 9.0 | 13.8 | 78.7 | 2.8 |
| v7 | concept-hybrid | 14.2 | 95.7 | 16.1 | 8.7 | 13.8 | 79.6 | 2.3 |
| v7 | plain-hybrid | 14.3 | 96.2 | 13.7 | 8.0 | 12.1 | 82.5 | 1.7 |
| v7 | plain | 9.2 | 97.0 | 12.1 | 7.9 | 10.5 | 84.9 | 1.6 |
| v8-strict | concept-hybrid | 9.9 | 95.3 | 17.6 | * | 15.4 | 77.7 | 2.2 |
| v8-strict | plain-hybrid | 11.9 | 96.1 | 14.2 | * | 12.3 | 82.0 | 1.9 |
| evalmitigate | advdoc | 9.8 | 92.4 | 8.9 | 6.4 | 7.4 | 83.5 | 1.4 |
| evalmitigate | onlydoc | 9.9 | 96.4 | 8.8 | 6.3 | 7.0 | 87.6 | 1.8 |
| advhyb (partial) | advdoc-hybrid | 11.0 | 92.0 | 10.8 | 7.3 | 9.5 | 81.2 | 1.3 |
| advhyb (partial) | advdoc-plainhybrid | 12.1 | 91.7 | 9.7 | 6.1 | 8.4 | 82.0 | 1.3 |

## Paired per task (number of samples, 0..3; wins/losses, two-sided sign test)

| run | pair | D_I | D_IO ref | D_IO full |
|---|---|---|---|---|
| v7 | concept-hybrid vs plain-hybrid | 36/21 p=.063 | 33/17 p=.033 | 32/17 p=.044 |
| v7 | concept-hybrid vs toolinput | 24/26 p=.89 | 23/20 p=.76 | 22/22 p=1 |
| v7 | concept-hybrid vs placebo-hybrid | 44/10 p=3e-6 | 38/8 p=9e-6 | 39/7 p=2e-6 |
| v8-strict | concept-hybrid vs plain-hybrid | 32/22 p=.22 | 29/20 p=.25 | 28/19 p=.24 |
| v8-strict | concept-hybrid vs toolinput | 23/29 p=.49 | 22/23 p=1 | 21/23 p=.88 |
| v8-strict | concept-hybrid vs placebo-hybrid | 39/15 p=.0015 | 33/13 p=.0045 | 34/12 p=.0016 |
| v8-strict | plain-hybrid vs toolinput | 22/41 p=.023 | 21/34 p=.11 | 20/34 p=.076 |
| evalmitigate | advdoc vs onlydoc | 22/20 p=.88 | 19/17 p=.87 | 17/18 p=1 |
| advhyb (partial, 160 dropped) | advdoc-hybrid vs advdoc-plainhybrid | 14/8 p=.29 | 13/6 p=.17 | 13/7 p=.26 |

## Reading
- **Validity is not the bottleneck.** 92–98% of inputs satisfy the contract, and almost every sample (110–113 of 113)
  has at least one valid input.
- **The fault-hypothesis gap is the largest loss.** Per sample it is 35–65 tasks per run; per assertion only 9–18% of
  inputs reveal the bug. The hybrid arms with concepts or tools (toolinput, concept-hybrid) make this gap smallest.
  The doc-based arms (advdoc, onlydoc) do not make it smaller than plain.
- **The output-validation gap depends on the oracle.** With the LLM's own expected values (o0) it is large: 10–29
  tasks per run, largest for the arms that find the most bug-revealing inputs (toolinput 28.7, concept-hybrid 23.3).
  With ref it shrinks to 6–11. So o0 hides most of the input-side gain, and ref/full recover most of it.
- **The concept effect is on the input side.** In v7, concept-hybrid gets 8.0 more D_I tasks per run than
  plain-hybrid, and 9.4 more D_IO(ref).
  - On D_I alone the v7 comparison is not significant (36/21, p = .063). It becomes significant only after the ref
    oracle (33/17, p = .033).
  - In v8-strict (same budget rule in round 2) the comparison is not significant at either level (D_I 32/22, p = .22).
  - concept-hybrid does not beat toolinput on D_I in either run (24/26 and 23/29).
  - The only robust result is against placebo-hybrid.

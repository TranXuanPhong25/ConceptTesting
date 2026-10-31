# Agentic PBT: pattern audit ($0)

Paper: Maaz, DeVoe, Hatfield-Dodds, Carlini, *Agentic Property-Based Testing*, arXiv 2510.09907.
Source: github.com/mmaaz-git/agentic-pbt @ 7ac6a15 (no LICENSE file). Read-only clone in the session scratchpad;
no author file changed, no model call.

Question: the prompt (`paper/hypo.md`, "Propose properties") lists 8 property patterns. Is this list (= the
concept slot we would swap) where the report quality comes from? Go/no-go before any paid swap run.

Data: `paper/results/` (933 Claude Code calls, 984 bug reports), `paper/score_results_final.csv`
(Opus 4.1 rubric score 0–15 for all 984; manual `valid`/`reportable` only for the top 21).
Script: `analysis/pattern_audit.py` → `analysis/pattern_audit.json`.

## Result 1: pattern label vs yield and score (rule-based labels)

| pattern | tests | % tests | reports | % reports | reports/1k tests | mean score | valid (of labeled) |
|---|---:|---:|---:|---:|---:|---:|---|
| invariant | 5507 | 38.3 | 291 | 29.6 | 53 | 10.45 | 4/5 |
| other (no rule) | 3413 | 23.8 | 260 | 26.4 | 76 | 11.02 | 7/7 |
| round_trip | 1723 | 12.0 | 108 | 11.0 | 63 | 11.33 | 2/2 |
| claim (docstring, outside list) | 1688 | 11.8 | 127 | 12.9 | 75 | 11.36 | 4/5 |
| math | 701 | 4.9 | 30 | 3.0 | 43 | 11.57 | 0/1 |
| inverse_ops | 440 | 3.1 | 21 | 2.1 | 48 | 10.62 | 0/0 |
| single_entry | 396 | 2.8 | 71 | 7.2 | 179 | 10.55 | 1/1 |
| multi_impl | 373 | 2.6 | 24 | 2.4 | 64 | 9.79 | 0/0 |
| metamorphic | 105 | 0.7 | 4 | 0.4 | 38 | 11.50 | 0/0 |
| confluence | 14 | 0.1 | 1 | 0.1 | 71 | 15.0 | 0/0 |
| no test block | – | – | 47 | 4.8 | – | 10.11 | – |

Rule accuracy is low: on the 21 hand-labeled reports my reading agrees with the rule label 11/21. Read the
table as shape only.

## Result 2: the 18 valid bugs, read by hand

- Listed patterns ≈ 11/18: crash/single entry 3–4, invariant 3–4 (hash/eq contract, output format, operand
  not mutated), round-trip 2–3, inverse ops 1 (register/provide).
- Outside the list ≈ 7/18: a specific behavior from the docstring with a hand-written expected value
  (LRU order for falsy values, `item_hash` ≠ hash of "null", `positive_integer` rejects 0, inverted
  `has_changes`, validator accepts strings, …).

## Reading

1. The list does shape what the agent writes: ~64% of tests carry a listed pattern.
2. Quality does not follow the pattern: mean rubric score is flat (9.8–11.6, all ≈ overall 10.8), and the
   unlisted docstring-claim tests are as productive as listed ones. The highest yield is crash checks
   (179 per 1k tests), which need no property at all.
3. What the prompt uses to control false alarms is "only test properties the code explicitly claims" plus the
   triage rubric, i.e. oracle/validity, not the pattern names. Same bottleneck as in our v41/v48/v64.
4. No no-list arm exists in the saved data, so this is observational; it gives no evidence that the pattern
   slot matters, and no evidence against an ablation either.

## Cost

Saved logs: $5,474 for 933 calls, median $5.81 per call (Opus 4.1, ~100 turns). A 4-arm swap on 33 tasks
would cost ~$770 with Opus; a cheaper writer moves into the regime where our runs were at ceiling
(Haiku v55h/v64) or placebo-level (Qwen v26: 19% unsound properties).

## Verdict

NO-GO for a paid pattern-swap run. The concept slot of this paper is not where its bug quality comes from,
and the run is >30× the remaining API budget.

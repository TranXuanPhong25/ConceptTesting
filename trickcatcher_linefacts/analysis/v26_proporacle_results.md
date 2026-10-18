# v26_proporacle results — 2026-10-18 (Qwen2.5-Coder-7B, K=1)

Plan: `PLAN_PROPERTY_ORACLE.md`. Code: `pipelines/v26_proporacle/oracle_run.py`. PREREG + amendment 1 (bare-array
wrapping, format only) committed before outputs. Frozen outputs: `out/pipelines/v26_proporacle/humaneval/oracle/
{pilot20,diag16}/` (`score.json`); superseded `pilot20_attempt1_barearray/`.

Fixed pools (12 inputs/task, admissible + natively checked only): pilot20 235 inputs, 22 with PUT ≠ reference on
10/20 tasks; diag16 171 inputs, 31 discrepancies on 7/16 cases. One call per (task, arm). Model property code ran in
the sandbox on the real PUT output; the reference was used only after the freeze.

## pilot20 (primary)

| oracle | tasks confirmed | tasks with FA | TP inputs | false alarms | precision |
|---|---|---|---|---|---|
| exact_spec | 8 | 16 | 13 | 48 | 0.213 |
| exact_code | 8 | 14 | 13 | 53 | 0.197 |
| property | 6 | 13 | 16 | 92 | 0.148 |
| metamorphic | 4 | 11 | 17 | 78 | 0.179 |
| consensus exact_code ∧ property (secondary) | 4 | 8 | 8 | 26 | 0.235 |
| union (secondary) | 10 | 17 | 21 | 119 | 0.150 |

Property soundness (evaluator only): 134/699 property checks (19%) return False on the **reference** output,
120 error → model-written properties are often wrong or crash.

## diag16 (secondary)

| oracle | tasks confirmed | tasks with FA | TP | FA | precision |
|---|---|---|---|---|---|
| exact_spec | 6 | 11 | 26 | 29 | 0.473 |
| exact_code | 5 | 6 | 12 | 16 | 0.429 |
| property | 6 | 9 | 27 | 61 | 0.307 |
| metamorphic | 4 | 9 | 18 | 62 | 0.225 |
| consensus | 4 | 4 | 8 | 13 | 0.381 |

Property soundness: 85/501 (17%) fail on the fixture oracle's correct output.

## Verdict (registered rule)

Property and metamorphic do **not** beat either exact arm on precision, and confirm fewer tasks → **negative**.
With Qwen 7B, writing the concept as executable property/relation is less reliable than predicting the exact value:
~1/5 of properties are unsound, so they produce more false alarms. Consensus (exact ∧ property) has the highest
precision (0.235 / 0.381 vs 0.213 / 0.473) but halves recall — not a clear win.
Side observation: with the larger fixed pool (incl. v21 final inputs), plain exact oracles confirm 8/20 pilot tasks
(v21 arms: 1–4), i.e. input coverage still matters; the oracle remains the precision bottleneck (~0.2).

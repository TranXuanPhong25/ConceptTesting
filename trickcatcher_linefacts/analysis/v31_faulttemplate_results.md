# v31 fault-template results (vibepass_half, Qwen3.5-35B-A3B via OpenRouter, K=1)

Source: `out/pipelines/v31_faulttemplate/humaneval/faulttemplate/openrouter/vibepass_half/score.json`
(frozen generation, scored with independent references). PREREG: `pipelines/v31_faulttemplate/PREREG.md` (amendments 1–4b).

## Registered decision
Rule: fault-template is promising iff paired task detection wins > losses vs plain AND false-alarm tests ≤ plain.

| arm | tasks confirmed /33 | confirmed tests | false-alarm tests | tasks with FA | input-discrepancy tasks | wrong expected | contract-invalid | schema errors |
|---|---|---|---|---|---|---|---|---|
| plain | 15 | 55 | 32 | 14 | 19 | 10 | 4 | 2 |
| fault-template | **18** | 54 | **27** | 11 | 20 | 6 | 6 | 3 |
| template-only (no LLM) | – | – | – | – | 11 | – | 31 | – |
| template-random (no LLM) | – | – | – | – | 9 | – | 35 | – |
| witness-only (no LLM) | – | – | – | – | 0 | – | 0 | – |

- Paired detection: wins 103, 168, 69, 73; loss 56 → 4–1. FA tests 27 ≤ 32. **Rule met.**
- Unique-PUT view (32 distinct sources): same 4–1, 18 vs 15.
- Paired discovery (input exposes PUT ≠ reference): wins 101, 103, 168, 69; losses 46, 56, 74 (4–3).

## Caveats (they limit the claim)
- n = 33, K = 1; a 4–1 sign test is p ≈ 0.38 (two-sided). Descriptive only.
- Win 103 comes from plain's final call failing the schema (`reason` too long), so plain produced no tests. Wins
  that are not a schema failure: 3–1.
- Attribution is mixed. On 168, the template inputs alone already expose the bug (template-only 3 discrepancies). On
  69 and 73, the template inputs expose nothing, so the model found the bug itself, possibly steered by the site/type.
  On 103, the only concept is MISSING_CASE.
- Ranking vs random templates: 11 vs 9 tasks with an exposing input, so ranking adds little over the template pool.
  The domain filter still lets 31–35 contract-invalid template inputs through (not counted as FA: no expected value).
- Concept/template type match 62/143.
- No placebo arm with unlabeled template inputs; a positive claim needs that control and K ≥ 3 or the full 66.

## Run notes
- Cost $2.56 for 198 calls (≈12k reasoning tokens per call; DeepInfra fp8, every call finish=stop, 0 incomplete).
- Paused once at the OpenRouter workspace monthly budget ($2); resumed after the limit was raised. Pipeline code is
  byte-identical to registered commit 86f37f4 (amendment 4b); 13 stale ledgers of unrecorded arms archived outside
  the pipeline before resuming.

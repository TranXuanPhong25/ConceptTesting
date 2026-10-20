# v34 placebo results: fault concept vs the same template inputs without concept content

Source: `out/pipelines/v34_ftplacebo/humaneval/faulttemplate/openrouter/vibepass_half/score.json` (frozen, independent
references). PREREG: v34 section in `pipelines/v34_ftplacebo/PREREG.md`. Cohort vibepass_half (33 PUTs), K=1,
Qwen3.5-35B-A3B via OpenRouter. plain / fault-template / no-LLM arms are the frozen v31 records (hash-checked);
only template-placebo was generated ($1.56 including transport retries).

| arm | tasks confirmed /33 | confirmed tests | false-alarm tests | tasks with FA | discovery tasks | wrong expected | schema errors | incomplete calls |
|---|---|---|---|---|---|---|---|---|
| plain | 15 | 55 | 32 | 14 | 19 | 10 | 2 | 0 |
| fault-template | **18** | 54 | 27 | **11** | 20 | 6 | 3 | 0 |
| template-placebo | 12 | 44 | **23** | 14 | 16 | 10 | 5 | 5 |

## Registered rule (primary): fault-template vs template-placebo
- Paired task detection: wins 103, 132, 168, 36, 69, 73, 75, 96; losses 70, 77 → **8–2** (sign test p ≈ 0.11).
- False-alarm tests: fault-template 27 > placebo 23 → **rule NOT met** (the FA condition fails).
- Tasks with a false alarm go the other way (11 vs 14), and test precision is equal (0.67 vs 0.66): fault-template
  makes more tests overall, so more FA tests in absolute count.

## Secondary
- template-placebo vs plain: 2–5 (p ≈ 0.45). Giving the inputs without the concept does **not** help; it is slightly
  worse than plain. So the v31 gain (fault-template vs plain 4–1) is not explained by the template inputs alone.
- Placebo probe calls hit the 16k token limit 5 times (finish=length; cases 6, 73, 74, 168×2), giving schema errors in
  those probe rounds (finals all completed). Two of the eight wins (73, 168) are among them. fault-template and plain
  had 0 incomplete calls. Bare inputs seem to make the model reason longer.
- Discovery (an input exposes PUT ≠ reference): fault-template vs placebo 6–2.

## Reading
Direction favours the concept content (8–2 on detection, fewer tasks with FA, same precision), but by the registered
rule the concept arm does not pass, because its absolute false-alarm test count is higher. n = 33, K = 1;
placebo was generated a day after the v31 arms. Next step that would decide it: K = 3 or the full 66 PUTs for the
three LLM arms (other 33 PUTs, K=1: 297 calls ≈ $3.9; K=3 on the half: 594 calls ≈ $7.7), with precision or
tasks-with-FA registered as the false-alarm unit before that run.

## Run notes
Transport: 10 truncated HTTP bodies (OpenRouter keepalive then drop; resumed), then the OpenRouter workspace daily
budget ($2, 403) stopped 8 arms; resumed after the limit was raised. Resume prep (archiving 403 attempt logs and the
ledgers of unrecorded arms) was done outside the pipeline; pipeline code unchanged since registration (9446f96).

## Post-hoc mechanism check (exploratory, no API; added after the result)
Question: does the concept itself point at the bug? Using the frozen outputs and the references:
- Concept inputs expose PUT ≠ reference in only 11/33 tasks; the rank-1 concept in 6/33. The surviving alternative
  equals the reference on 13 exposing inputs in total (mostly case 132).
- In 5 of the 8 fault-template wins over placebo, no concept input exposes the bug. All 16 confirmed tests in the wins
  are new inputs written by the model (0 reused from the concepts).
- So the gain is not "the tool locates the bug and the LLM confirms it": the specific site/type hypothesis is usually
  wrong. What remains is a framing effect, and partly placebo's own weakness (bare inputs < plain, token overruns).
Go/no-go signal: weak. The lever is tool-side concept accuracy, measurable on CPU without any model call.

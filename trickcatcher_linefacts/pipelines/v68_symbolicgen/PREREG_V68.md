# PREREG v68 — v57 generation protocol with the v66 CrossHair evidence (Qwen-32B via ngrok)

Frozen 2026-10-25 before any v68 generator call and before any private score of v57 generation_v2 or v68.

## Question
v57's four-arm protocol ran (generation_v2) with empty evidence because its constructor built 0 inputs. v66 now builds
verified reach + local-difference + output-difference witnesses on 5/6 cases. With that evidence filled in, does the
**concept** arm (source-bound fault hypotheses as test obligations + verified witnesses) find more confirmed bugs than
**plain**, and is any gain due to the concept framing rather than to the raw evidence or the inputs alone?

## Protocol (frozen, = v57 runner except where stated)
- Cohort: the same six PUTs (61, 66, 124, 58, 131, 85; 5 problems), public requests unchanged.
- Model: ngrok `qwen2.5-coder-32b-instruct`, ctx 8192, serial, max 1536 output tokens/call, ≤2 transport attempts/slot.
- Shared writer call per case (3 proposals max): **reused** from v57 generation_v2 (same request identity, checked per slot).
- Plain arm: identical requests to v57 generation_v2 plain → **reused** (identity-checked). Not re-sampled.
- CPU: v66 CrossHair constructor on catalog (cap 48) + accepted writer proposals, per-hypothesis budget as v66.
- **New shared validity call** (1 per case, max 512 tokens): the same model judges, from the spec only, whether each of
  the ≤12 distinct verified inputs (evidence rank order) satisfies the input constraints. Only judged-valid inputs are
  shown; hypotheses with a judged-valid witness are ranked first (stable). Malformed verdict → no inputs shown.
- Arms (3 calls each: probe, probe, final; ≤6 tests/call; PUT observations fed back): `plain`, `concept`,
  `equal_evidence_raw` (same evidence object as concept, neutral framing), `inputs_only` (only the shown inputs).
  Top 3 hypotheses × ≤2 inputs displayed.
- New model calls: 6 validity + 54 arm calls = 60 (writer 6 + plain 18 reused).

## Scoring (pinned in protocol.json `evaluation_sources` before generation)
`analysis/v68_symbolicgen/score_v68.py` (v63 scorer adapted): raw final slots (6/arm/case); EvalPlus contract validity,
reference vs PUT; labels confirmed / input_discrepancy_wrong_expected / passing / false_alarm / invalid / unresolved.

## Decision (primary = tasks with ≥1 confirmed final test, per arm)
- **PROMISING** (justifies a separate, larger frozen PREREG): concept ≥ plain + 2 tasks AND concept ≥ equal_evidence_raw
  AND concept ≥ inputs_only.
- If concept gains but ≤ inputs_only → the effect is the constructed inputs, not the concept framing.
- Otherwise **NOT PROMISING**. No cohort enlargement, reruns or budget increases after outcomes (signal, not more data).

## Mechanism checks (reported, not decision)
Validity-judge precision/recall vs EvalPlus contract; share of shown inputs contract-valid; final tests reusing shown
inputs; confirmed tests whose input is a shown witness; evidence per case (verified hypotheses shown).
Secondary, descriptive: v57 generation_v2 scored with the same scorer (`--historical-v57`).

## Not claimed
No bug labels before freeze; small n (6 PUTs); one sample per slot; no v31-template arm in this run.

## Amendment 1 (independent Sonnet review PASS-with-fixes; before any CPU evidence was inspected or any new model call)
Review verified offline that all 6 writer + 18 plain requests match the v57 cache exactly. Applied before (re)running prepare-cpu
(an earlier pre-fix prepare-cpu was stopped without writing evidence):
- Context guard: evidence display shrinks (3×2 → 2×2 → 2×1 → 1×1 hypotheses×inputs) until ≤3000 chars; literals clipped at 300
  chars. Identical for concept and raw; inputs_only shows the same inputs.
- inputs_only text now says inputs were screened by a model; hidden-input counts split into judged-invalid vs not-judged.
- Scorer validity audit tolerates non-literal candidates.
- Decision unit: **primary = tasks_confirmed (6 PUTs)**; problem-level (5) secondary. Failed/missing final slots count as 6 missing
  tests for that arm (no rerun). If any evidence arm loses a final to `context_budget_exceeded`, that is reported as an interface
  failure and the comparison for that case is flagged. Results are descriptive (n=6, one sample/slot, plain reused); +2 is a
  screening threshold for a larger PREREG, not inference. Case 58 (0 constructed inputs) cannot discriminate concept from plain.

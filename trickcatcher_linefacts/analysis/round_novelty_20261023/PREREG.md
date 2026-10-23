# Round-novelty analysis (v11_fair dev, saved outputs) — PREREG

Registered 2026-10-23 (Claude), before any round-split outcome is computed. CPU only, no LLM call, no new generation.

## Motivation

Anthropic, "Solving code review at Anthropic" (claude.dev blog, 2026): when they ran `git blame` on what the
reviewer kept flagging in later rounds, about 59% was code that existed at the reviewer's first pass. Extra rounds
mostly re-found old issues rather than finding new ones. Our hybrid arms also have a second round (Hypothesis
strategies for the hints that round 1 missed). §11.41 showed the round-2 gain of concept-hybrid over placebo comes
mainly from the number of round-2 requests, not from hint content (26/22, p = .67). This analysis asks the
mechanism question directly: what does round 2 add that round 1 did not already have, and does real hint content
make round 2 more novel than matched placebo hints?

Prior art in this repo: §11.37 witness-only (about 2/3 of toolinput's bugs already sit in the fuzz witnesses),
§11.41 v11_fair dev (concept-hybrid 61.0, placebo-hybrid 57.7, plain-hybrid 55.7, concept 48.0, plain 45.0),
v9 §11.36 (round 2 with concrete calls adds 6/0 tasks). None of them splits detections by round and checks round-2
novelty against round 1 and against the tool witnesses.

## Data

- Generation: `pipelines/v11_fair/out/humaneval/generation` (eval.jsonl, dev split, 113 tasks, K = 3).
- Oracle: `pipelines/v11_fair/out/humaneval/oracle`, **ref** mode only. Executions are replayed exactly as
  `analysis/final_protocol.py` does (same functions imported, PYTHONHASHSEED 12, temporary output only).
- Witnesses: bundle `tool_inputs`, scored as in `final_protocol.py` (witness-only arm).

## Gate (before any outcome)

Per-arm whole-sample detecting samples and failing / correct-failing assertion counts recomputed from the replay
must equal `analysis/final_protocol_v11_dev.json` (ref) for plain, concept, concept-hybrid, placebo-hybrid,
plain-hybrid, toolinput and witness-only. Any mismatch → STOP and report the mismatch only.

## Definitions (hybrid arms: concept-hybrid, placebo-hybrid, plain-hybrid)

For each (task, sample): the first `len(round1_assertions)` assertions are round 1 (R1, prefix equality checked);
the rest are round 2 (R2). Calls = distinct normalized calls; an R2 call equal to an R1 call is counted as a repeat
and belongs to R1 only.

- `det1` = an R1 call detects (emitted, valid, canonical-correct expected value, PUT fails); `det2` = an R2 call
  detects; whole sample detects iff `det1 or det2`.
- `r2_new` = `det2 and not det1` (round 2 found a bug that this sample's round 1 missed).
- `r2_redundant` = `det2 and det1` (round 2 re-finds a bug round 1 already found). Redundancy share =
  r2_redundant / det2 (the blog's 59% analog).
- `r2_new_beyond_tool` = `r2_new` on a task where witness-only does not detect; `r2_new_tool_reachable` otherwise.
- Conditional novelty = r2_new / #samples with `not det1`.
- Same split for D_I (input reveals a PUT/canonical discrepancy, oracle-independent), to separate reach from oracle.
- Round-2 harm: R2 false alarms = R2 calls with failing and not correct-failing; samples where R2 adds the first
  correct-program flag (none in R1).

## Comparisons

Per-task counts over the K = 3 samples, two-sided sign test over tasks (113 clusters), as in `final_protocol.py`.

- **Primary:** concept-hybrid vs placebo-hybrid on per-task `r2_new` count.
- Secondary: concept-hybrid vs plain-hybrid on `r2_new`; concept-hybrid vs placebo-hybrid on `det2`,
  `r2_new_beyond_tool`, conditional novelty (descriptive) and R2 false alarms (lower is better).
- Task-level sets: tasks with any `r2_new` sample per arm, with overlaps between arms.

Caveat registered now: R1 differs between arms (concept R1 = concept arm, placebo R1 = placebo hints, plain R1 =
plain), so `r2_new` depends on how many samples R1 missed; conditional novelty is reported beside it.

## Decision rule (fixed before scoring)

- **SIGNAL** that hint content drives round-2 novelty: concept-hybrid > placebo-hybrid on per-task `r2_new` with
  p < .05 **and** concept-hybrid `r2_new_beyond_tool` ≥ placebo-hybrid's. A signal only justifies writing a separate
  plan for a round-2-targeted concept design; it does not authorize a run.
- **NO SIGNAL** otherwise: round-2 novelty is attributed to request budget / Hypothesis sampling, consistent with
  §11.41. No new run is proposed from this analysis.
- Redundancy share and round-2 harm are descriptive (thesis "what extra rounds add" paragraph), no gate.

## Outputs

`round_novelty.py` (execute → cache outside the repo, score → `RESULTS.md` + `results.json` here). Execution cache
lives in the session scratchpad; it is reproducible from the command in the script docstring.

## Amendment 1 — 2026-10-23, after independent review, before any round-split outcome

Independent read-only review (structural counts only, no outcomes) found:

- Data facts: `round1_assertions` is a prefix in every row, `dropped_assertions` = 0, R2 never repeats an R1 call
  (strict round 2 removes seen inputs; repeats are now asserted to be 0). concept-hybrid R1 = concept arm 339/339,
  plain-hybrid R1 = plain arm 339/339. The R2 cap dropped inputs in 3 placebo and 2 plain rows (negligible). In ref
  mode the oracle supplies expected values, so `== None` placeholders do not change detection.
- **Round-2 input imbalance:** round-2 requests are matched per (task, sample), but the inputs actually delivered are
  not: R2 calls concept-hybrid 354 (135 samples with R2), placebo-hybrid 926 (198), plain-hybrid 890 (163). Raw
  `r2_new` therefore mixes hint content with input yield and is biased toward placebo.

Changes:

1. **Decision now uses a budget-matched co-primary.** Per (task, sample), n = min(R2 calls of concept, R2 calls of
   placebo); matched `r2_new` = 0 if `det1`, else the probability that a random n-subset of the R2 calls detects
   (`final_protocol.cut`, 100 draws, seed `20261013-round-novelty-matched`). Per-task sums, sign test.
   SIGNAL = matched co-primary concept > placebo with p < .05 **and** concept `r2_new_beyond_tool` ≥ placebo's.
   The raw `r2_new` comparison stays as registered primary but is descriptive (what round 2 actually adds per arm).
2. NO SIGNAL wording: "under a matched round-2 input budget, real hints do not make round 2 find more bugs that
   round 1 missed than placebo hints". It no longer attributes novelty to "request budget".
3. Input yield (R2 calls per arm) is reported as a mechanism finding; it is not part of the decision.
4. Round-2 false alarms are reported per R2 call (fa2 / R2 calls); the raw count sign test is shown but not interpreted.
5. placebo-hybrid vs plain-hybrid on `r2_new` is exploratory.
6. Gate also checks `D_I`, `D_I_samples`, `false_alarms`, and that each hybrid arm's round-split `whole` equals the
   saved `detecting_samples`.
7. The D_I split is partial (reach only: `di1`, `di2`, `di_new`); no beyond-tool D_I.
8. `RESULTS.md` is written by hand from `results.json` after scoring.

# v52 pilot: does the v49 definitional concept help a stronger program writer (Claude Sonnet)?

Written 2026-10-24 (Claude) before any Sonnet call. User request: "spawn claude sonnet làm vài task xem nó có tốt hơn
không (concept có giúp không)". Exploratory pilot: no GO/NO-GO claim, signal only; never enlarged to rescue a result.

## Question
v49 (Qwen2.5-Coder-32B): the ENUMERATE/CHECK/AGGREGATE concept (`defn`) beat `brute` by 2 tasks, only through more valid
programs; on tasks where both had ≥ 2 valid programs they were identical. Does the concept change anything for a
stronger writer, and is the brute-force spec oracle better with Sonnet?

## Design (everything else = v49)
- Writer: Claude Sonnet (Claude Code subagent, `model: sonnet`), one independent subagent per program, k = 3 per arm per
  task, arms `defn` and `brute`, prompts = exact v49 `gen.messages` (spec + public tests + signature; no PUT code).
  Each subagent may use exactly two tools: Read its prompt file, Write its answer file; tool count is checked from the
  run report and any program whose subagent used other tools is excluded (reported).
- Tasks (rule fixed before any call, uses v49 Qwen outcomes): tasks with ≥ 1 exposing input in the v49 decisive
  universe and not confirmed by both Qwen `defn` and `brute`; one per distinct problem; first 6 by sha256(`v52/<task>`):
  **141, 46, 87, 65, 161, 103** (Qwen at k = 5 confirmed only 103 with `defn`). Selected for Qwen failures, so the
  Sonnet–Qwen comparison is not a cohort estimate.
- Validity, inputs, execution (1 s per call, chunked), quorum (≥ 2 and > V/2), cap 20 tests/task, judging: v49 code on
  the v49 decisive universe and v49 reference cache (no new reference semantics).
- Comparison: Sonnet defn vs Sonnet brute (concept effect); Sonnet vs Qwen on the same tasks with Qwen's first 3
  programs (k-matched) and Qwen k = 5 (v49 score).
- Report per task and arm: valid programs, confirmed (0/1), correct assertions, tests, FA tests, concept-comment presence,
  AST similarity to the PUT (memorization proxy).

## Caveats (stated before results)
Sonnet's training data likely contains these LeetCode problems (VibePass is from LiveCodeBench); a win may be recall,
not the concept. 6 tasks × 3 programs is a pilot: a difference of 1–2 tasks is not evidence.

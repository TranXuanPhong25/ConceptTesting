# v53 pilot: does the fault concept help a stronger test writer (Claude Sonnet) in the v34 loop?

Written 2026-10-24 (Claude) before any Sonnet call or v53 output. User request: "thử spawn claude sonnet làm vài task xem
nó có tốt hơn không (concept có giúp k)". Exploratory pilot: a signal, not a claim; never enlarged to rescue a result.
Complements v52 (another session: Sonnet writes *oracle programs* with the v49 definitional concept). v53: Sonnet writes
*tests* with the v31/v34 fault concept, the only concept arm that once met a registered rule (v31 18 vs 15, Qwen3.5).

## Prior art (version tree)
v31 fault-template vs plain (Qwen3.5-35B, 18 vs 15 /33, rule met, weak); v34 placebo control (8–2 vs placebo but FA
27 > 23, rule not met; post-hoc: concept inputs rarely expose the bug, gain looks like framing); v27/v28 Codex (strong
model) on HumanEval pilot20: ceiling 16–17/20 in every arm, no concept gain; v29 VibePass Codex invalid (reference leak
through a `_plus` field). New here: a stronger model than Qwen on VibePass (not at ceiling for Qwen), same frozen
concepts and loop, with the v34 placebo.

## Design (everything = v34 except the model)
- Code: `pipelines/v34_ftplacebo` unchanged (`FTRun.ft_arm`, `guidance`, `placebo_guidance`, schemas, replay tool,
  `score_record`, `Reference`). The driver `run.py` only swaps the LLM client for a file client and restricts cases/arms.
- Concepts: v34's frozen `tool.json` per task copied byte-for-byte (sha256 checked), so all arms see the same
  concepts/inputs as Qwen did.
- Arms: `plain`, `fault-template`, `template-placebo`; loop = probe round 1 → PUT replay feedback → probe round 2 →
  final (≤ 6 tests). Each LLM call is answered by **one fresh Claude Sonnet subagent** (Claude Code `model: sonnet`)
  that reads the exact request (system + user message, as sent to Qwen) and writes its raw answer to a file. Calls are
  stateless as for Qwen (history comes only through `earlier_feedback`). Subagents are told to use only Read (the
  request file) and Write (the answer file); no Bash, no other files. Invalid JSON = schema error, as for Qwen (no retry).
- Tasks (rule fixed before any call; uses only v34 Qwen outcomes): vibepass_half tasks where not all three v34 LLM arms
  confirmed; one per distinct problem (groups 3/96, 39/58, 46/75/77, 61/65/66, 69/70, 73/74/161); first 6 by
  sha256(`v53/<task>`): **141, 39, 56, 36, 132, 70**. Selected for Qwen failures: not a cohort estimate.
- Scoring after all 54 calls exist and the run is frozen: v34 `score_record` with v34 `Reference` semantics
  (contract-invalid with a disagreeing expected = FA). Reported per arm: confirmed tasks, confirmed tests, FA tests,
  tasks with FA, input-discrepancy tasks, schema errors; Qwen3.5 v34 numbers on the same 6 tasks beside them.

## Signal rule (stated before results)
Concept-help signal iff Sonnet `fault-template` confirmed tasks ≥ `plain` + 2 **and** ≥ `template-placebo` + 2, with FA
tests ≤ `plain`'s. Otherwise: no signal for this concept with a stronger writer. Mechanism check (reported): share of
confirmed tests whose input comes from the concept/template inputs vs written by the model (v34 post-hoc question).

## Caveats (before results)
K = 1, 6 tasks: a 1-task difference is noise. Sonnet may know these LiveCodeBench problems (recall, not concept).
Subagent tool use cannot be fully sandboxed; the instruction restricts it and the run notes report any deviation seen.

## Amendment 1 (2026-10-24, after the independent read-only review; round 1–2 answers exist, no final call, no score)
Review verdict: no code bug; fidelity (same slots/digests, loop, `final_inputs`, `score_record`), replay and leakage checks
passed. Applied before any final call or outcome:
- M1 (partial-read risk): `wave` is run only after every subagent of the wave has finished (done for rounds 1–2), and
  `score` re-validates every response file and requires it to equal the recorded value (exactly one file per
  task/arm/stage), else refuses.
- N1: `tool.json`, `protocol.json` and the subagent prompt are in the freeze; `score` re-checks tool.json against v34.
- N2/N6: Qwen columns for every reported metric (confirmed tests, FA tasks, discrepancy tasks, schema errors); the
  guidance-input mechanism is also reported as a share (plain's share is the coincidence baseline).
- N3: the verbatim subagent wrapper prompt and the resume message are saved (`subagent_prompt.json`).
- Run note: round 2 was interrupted by a Claude session limit (HTTP 429) after 15/18 answers were written; the 3
  missing calls (56 plain, 56 placebo, 141 placebo) were completed by resuming the same subagents. Rounds 1–2: 36/36
  answers schema-valid. Subagent tool use: 3 per call (Read, Write, hand-back), 2 for the resumed ones.
- Known arm-neutral difference vs Qwen (reported, not fixed): no `response_format=json_object`, no empty-answer retry;
  compare schema errors with Qwen with care.

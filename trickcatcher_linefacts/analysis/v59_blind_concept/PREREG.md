# v59 pilot: fault concept as the only channel of PUT information for a code-blind strong generator

Written 2026-10-24 (Claude), before any v59 prompt, call or output. User: "thử hết cho t" (direction 1 of 3: a concept
that carries information the writer cannot derive itself). Exploratory pilot: signal only, no GO claim, never enlarged.

## Why this and not another concept run
- Strong writers read code: with the PUT visible, the v34 fault concept = placebo for Sonnet (v53_sonnet_tester, 5/6 in
  every arm) and Codex (v28 ceiling). Concept content is redundant when the writer sees the code it was derived from.
- The strongest pipeline so far (v53_validity_smallscope Stage 2: Sonnet `defn` oracle + `open` filter + Sonnet `plain`
  generator, 24/33, precision .96) uses a **code-blind** input generator (statement, public tests, signature only;
  `smallscope.message`). Six tasks are reached by no Stage 2 arm: **6, 39, 48, 58, 69, 70** (RESULTS_STAGE2.md).
- For a code-blind generator the concept is the only carrier of PUT information, so here the concept *can* carry
  information the writer cannot derive. Question: does the v34 fault concept make the generator reach these bugs, beyond
  the same template inputs without concept content (placebo), and how close does it get to simply showing the code?
- Not duplicated elsewhere: v55 (Codex) tests an interpretation concept on the oracle (73/74/161 class); v56 is a fresh
  cohort for that pipeline; v58 is queued for UTGen error patterns. Input-side concepts were null for code-visible or
  tool-only selectors (v41/v44/v47/v48/v53 Stage 2); none gave PUT information to a code-blind writer.

## Tasks (fixed by rule before any call)
All vibepass_half tasks that no Stage 2 input arm reached: 6, 39, 48, 58, 69, 70 (problems q3233; q3781 = 39, 58, byte-
identical PUTs; q3478; q3658 = 69, 70). Selected on Stage 2 failure: not a cohort estimate.
Known harness limit (stated before results, from v45/Stage 2 diagnostics): on 6, 39 and 58 every known exposing input
needs size ≥ 78 / n ≥ 55 and the PUT exceeds the frozen 1 s per-call limit there, and generator literals over 4000
characters are dropped; these tasks are kept in the denominator but are unlikely to be confirmable by any arm.

## Arms (writer: Claude Sonnet subagents, `model: sonnet`, fresh context per batch)
Common prompt = Stage 2 `plain` generator prompt, byte-identical (`smallscope.message(task, 'plain')`, system
`validity.SYSTEM`): statement, public tests, signature, "Define inputs() returning between 100 and 300 distinct small
valid inputs most likely to reveal a bug in a plausible but incorrect solution" + SHARED rules. Arms add one block between
the signature and the instruction:
1. `blind`: nothing (= Stage 2 `plain`, fresh samples).
2. `concept`: "Tool analysis of the program under test (its code is not shown):" + the v34 fault-template guidance
   (`ft_run.guidance(tool)`, frozen v31 tool.json: ranked fault concepts with fault type, meaning, site line, site code,
   alternatives, evidence, template inputs with the PUT's output).
3. `placebo`: "Tool output for the program under test (its code is not shown):" + `ft_run.placebo_guidance(tool)` (the
   same template inputs with the PUT's output, no site, type, alternative, hypothesis or rank).
4. `code`: "Program under test (may be buggy):" + the PUT source. Reference arm (does the code itself carry it?).
k = 3 independent samples per arm. Unit of generation = distinct prompt (39/58 prompts are identical in every arm;
69/70 and 39/58 share the `blind` prompt): one answer per (arm, sample, distinct prompt), shared by tasks with that prompt.
Batches: one subagent per (arm, sample), answering that batch's distinct prompts; tools limited to Read (own request
files) and Write (own answer files); the subagent prompt is frozen in `subagent_prompt.txt` before the first spawn.

## Oracle, filter, scoring (frozen, identical for all arms; references only in `score`)
Stage 1 `open` validity checks (public drop rule) and the Stage 2 Sonnet `defn` oracle programs (k = 3; v52 programs
for v52 tasks), resource-tolerant primary / strict sensitivity, v49 primary quorum, cap 20 tests per task in sha256
order, v48/v49 official-path judging — the Stage 2 `score` code path, copied with this experiment's own execution and
reference roots (Stage 2 caches untouched). Per task and arm, inputs = accepted literals of sample 0, then 1, then 2,
each sample capped at 300 (Stage 2 CAP), deduplicated.
Primary: confirmed tasks /6. Secondary: reach (any accepted contract-valid input where PUT ≠ reference on the official
path), confirmed tests, FA tests, precision; per-answer reach (mechanism: each of the 3 samples alone); for `concept` and
`placebo`, the share of exposing / confirmed inputs equal to a template input (literal equality) and the share outside
them; `code` reported as reference.

## Signal rule (registered; pilot)
**Signal** iff `concept` confirmed tasks ≥ `placebo` + 2 and ≥ `blind` + 2, the extra tasks span ≥ 2 problems,
`concept` FA tests ≤ min(`placebo`, `blind`) FA + 5, and `concept` precision ≥ .8. Otherwise **no signal**. If reach
differs but confirmation does not (oracle-bound), report it as a mechanism finding, not a signal.

## Caveats (before results)
6 tasks / 4 problems, k = 3: a 1-task difference is not evidence. Sonnet may recall these LeetCode problems. The concept
leaks site code lines; that is the treatment (PUT information), and `code` bounds it.

## Amendment 1 (2026-10-24, after the independent read-only review; before any score, reference read or outcome)
Dispatch 1 (57 answers) was generated in parallel with the review, which then found two must-fixes in how requests were
handed to writers. Those answers are **discarded unscored** (moved to `out/.../discarded_dispatch1/`, only checked to start
with a code block) and every answer is regenerated:
- **M1 arm name visible:** request/answer paths contained the arm name (`requests/placebo/...`) while subagents inherit
  project context (memory says concept ≈ placebo). Now writers see only neutral paths
  `~/.local/state/ct_jobs/<10-hex>/{r,a}_<key>.txt`, hex = sha256(secret salt/arm/sample/batch); the mapping lives in
  `manifest.json` (written after generation); answers are copied into `out/.../answers/<arm>/s<i>/` by `collect`.
- **M2 same problem in one batch:** 69 and 70 (problem q3658) were answered by one writer in the non-blind arms (cross-task
  information only there). Now no batch holds two requests of the same problem: per (arm, sample) the non-blind arms use
  two writers ({6, 39/58, 48, 69} and {70}); `blind` keeps one writer (one prompt per problem).
- **S9 code view:** the `code` arm shows `task_view(case)['source_masked']` (comment-masked, as in v34/v53 code-visible
  arms) instead of the raw source.
- **S5 audit:** a writer must use exactly 2n+1 tool calls for n requests (n Read, n Write, hand-back), as reported by its
  completion notice, recorded in `audit.json`; a violating batch is regenerated once with a fresh writer, then excluded.
- **S4 parse:** an unparseable answer is regenerated once before freeze; `score` refuses to run if any frozen answer is
  unparseable.
- **S3/S8 guards:** `freeze` also hashes run.py, the request files, manifest, subagent prompt, the v31 tool.json files and
  the Stage 1 `open` / Stage 2 oracle answers that scoring reads; `score` re-checks every frozen hash.
- **S6 reporting:** oracle rejection reasons, strict confirmed tasks and finishing reach are added to the totals.
- **S7 uninformative outcome:** if `code` also reaches 0 tasks, the result is harness/oracle-bound and **uninformative**,
  not a concept null.
Clarification (same time, before regeneration): `manifest.json` (job directory → arm/sample mapping and salt) is written
by `prompts` into the experiment output folder, which no writer is given or allowed to open.

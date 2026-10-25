# v60: behaviour-fact concept for a code-blind Qwen input generator

Written 2026-10-25 (Claude), before any v60 call or output. User: "thử mấy cái hướng còn mở đi … đừng chạy sub agent
nữa, quá tốn, chạy qwen thôi". Open direction from v59: a concept must state the *specific behavioural fact* (a cap, a
condition, a special case), not a fault-type label. Writer and fact extractor: Qwen2.5-Coder-32B (user's endpoint,
1 worker, 900 s client timeout as v49). No Claude subagents: the independent-review rule is replaced by a self-review
checklist (recorded below) because the user forbade subagents.

## Prior art (version tree)
v7 line facts / v34 fault concepts to a code-visible writer (concept = placebo); hạng 3 trigger inference (offline only,
never run with an LLM); v59 (Sonnet, code-blind generator: fault concept 1/6 = blind < code 3/6 on 6 hard tasks).
New: facts phrased as behaviour under input conditions, extracted from the PUT, given to a writer that cannot see the
code; all 33 vibepass_half tasks; Qwen writer.

## Calls (all temperature/seed fixed here)
1. `facts` (concept source), one per task: system = validity.SYSTEM-style plain text; user = statement, public tests,
   signature, PUT source (comment-masked, `task_view['source_masked']`), instruction: "List up to 5 BEHAVIOUR FACTS of
   this code: specific conditions on the inputs under which it takes a special path, uses a limit or constant, skips,
   caps or stops work, or treats an input class differently. One line each: `FACT: when <condition on the inputs>, the
   code <does what>`. Describe what the code does; do not judge whether it is correct; no other text."
   temperature 0, max_tokens 512.
2. `specfacts` (placebo source), one per task: same, without the PUT source, instruction "List up to 5 facts the problem
   statement implies about the answer: one line each `FACT: when <condition on the inputs>, the answer <is what>`; no
   other text." temperature 0, max_tokens 512. Same format and budget, no PUT information.
3. Generator (`smallscope.message(task, 'plain')`, the Stage 2 code-blind prompt, system `validity.SYSTEM`), k = 2
   samples, temperature 0.8, top_p 0.95, max_tokens 1536, seed = sha256(`v60/<arm>/<key>/<i>`)[:8]. Arms insert one block
   before the instruction: `blind` none; `concept` "Facts about the program under test (its code is not shown):\n" +
   FACT lines; `placebo` "Facts about the problem:\n" + spec FACT lines; `code` "Program under test (may be buggy):\n" +
   masked source. Only `FACT:` lines are passed on (others dropped, counted); 0 lines = empty block (counted).
Generation unit = distinct prompt (identical prompts of sibling tasks share answers, as v59). ~310 calls.

## Scoring (frozen; references only in `score`)
v59 `score` path unchanged except arms/tasks/k: Stage 1 `open` filter, Stage 2 Sonnet `defn` oracle (frozen answers; v52
programs for v52 tasks), primary quorum, cap 20, official-path judging, own execution/reference roots. Per task and
arm inputs = accepted literals of sample 0 then 1 (≤ 300 each).

## Decision (registered)
**Signal** iff `concept` confirmed tasks ≥ `placebo` + 3 and ≥ `blind` + 3, the extra tasks have positive per-problem net
on ≥ 3 problems (24 problems; sibling tasks share a problem), `concept` FA tests ≤ min(`placebo`, `blind`) + 5, precision
≥ .8. Otherwise **no signal**. `code` is the reference: `concept` ≥ `code` would mean the extracted facts are more usable
than the raw code for this writer (reported, no gate). If `code` ≤ `blind`, the writer cannot use PUT information at all
and the result is **uninformative** for the concept question.
Mechanism (report): per-answer reach; FACT lines per task; manual audit of whether a fact names the bug-relevant condition
on tasks where `concept` and `code` differ.

## Self-review checklist (done before generation, recorded in CHANGELOG)
prompt fidelity (blind = Stage 2 plain bytes), no reference/hidden text in any prompt, k and seeds per arm equal, oracle
and filter identical across arms, freeze hashes all answers + external files before `score`.

## Caveats
Selected tasks are the dev half (24 problems); Qwen may recall LeetCode problems; the oracle is Sonnet's (fixed for all
arms, so only the input side differs); a 1–2 task difference is not evidence.

## Amendment 1 (2026-10-25, after the Codex read-only review; after generation, before freeze or any score)
- **M1 answers frozen:** `frozen.json` hashes `answers/*.txt` (what `generated()` reads); `freeze` checks every answer
  equals its call record's text and every call's digest equals its prompt/params (facts, specfacts, generator).
- **M2 external scope:** also frozen: v49 task records (PUT outcomes, universe), v41 PUT/reference caches of all 33 tasks,
  helper sources (v49 oracle, v53 smallscope/validity, v59 run, v48 e2e, iorel); absent externals block `freeze`;
  `score` re-checks the frozen state before and after scoring.
- **M3 verdict precedence:** as registered ("If `code` ≤ `blind` … **uninformative**"), `uninformative` overrides `signal`;
  the signal checks are still reported (`signal_checks_passed`).
- **Reporting (S3, notes):** per-problem confirmed tasks, generator status (parse/sandbox failures) and finish reasons per
  arm; the claim is about the whole treatment package (block + header), and budgets are equal per task, not in aggregate
  (blind/placebo have 24 distinct prompts, concept/code 32).
- **Correction (Codex S4):** task 75 did **not** overflow (facts 1,813 and code 1,823 input tokens, all `stop`); the
  CHANGELOG estimate used the raw source length. The overflow → empty-answer policy is now stated here; it did not apply.

# v54 pilot (registered as v53_sonnet_mutconcept; renumbered 2026-10-24 after a v53 collision with another session's v53_sonnet_tester): does the mutant fault concept help a stronger variant writer (Claude Sonnet) in the TC oracle?

Written 2026-10-24 (Claude, session 28d298da) before any Sonnet call. User request: "thử spawn claude sonnet làm vài
task xem nó có tốt hơn không (concept có giúp k)". Exploratory pilot: no GO/NO-GO claim, signal only; never enlarged to
rescue a result. Companion of v52 (another session: v49 definitional concept, Sonnet spec programs); v53 covers the other
concept kind on the oracle side, the v46 mutant fault concept given to the TC variant writer.

## Prior art
v46 (Qwen2.5-Coder-32B TC variants `tc` vs `tc_concept`, scoring pending), v48 (Qwen TC variants as oracle: NO-GO, oracle
binds: common-mode 9 tasks, no valid variant 7), v27/v28 (Codex ≫ Qwen as oracle on HumanEval, tool-less Codex at the
ceiling 16–17/20 with no concept gain), v29 (VibePass Codex, invalid: reference leak). A strong writer on VibePass with
the mutant concept has not been tested.

## Design (everything else = v46 program arms)
- Writer: Claude Sonnet (Claude Code subagent, `model: sonnet`), one independent subagent per program, k = 3 per arm per
  task, arms `tc` and `tc_concept`, prompts = the exact v46 `tc_messages` (TrickCatcher variant template + PUT source;
  `tc_concept` adds the v46 concept block, ≤ 5 distinct mutant edits). `prompts` checks each prompt against the v46
  cached Qwen record digest (same messages). The subagent may use exactly two tools: Read its prompt file, Write its
  answer file (the raw reply). A program whose subagent used any other tool, or wrote no answer, is excluded (reported).
- Tasks (rule fixed before any call; uses saved Qwen/reference outcomes): v42 D1 tasks (a package question whose input
  exposes the bug and whose mutant output equals the reference), minus 75 (Qwen TC prompt overflows 8192 tokens, no
  Qwen comparison), minus tasks confirmed by every v48 arm with Qwen TC variants (36, 61, 121, 131, 132, 164), one per
  problem (`question_id`), first 6 by sha256(`v53/<task>`): **85, 141, 46, 65, 101, 161**. Selected where the Qwen TC
  oracle failed and the concept is plausibly informative, so the Sonnet–Qwen comparison is not a cohort estimate.
  Overlap with v52: 141, 46, 65, 161.
- Oracle and scoring = v46 code (`oracle.py`): PUT preamble loading, validity on the public base inputs, question inputs =
  the task's v46 question inputs, tc-full vote (largest group of valid outputs that differ from the PUT), consensus rule
  (≥ 3 valid, all agree, ≠ PUT), confirmed = contract-valid input, PUT ≠ reference (batch and official), value `same` as
  the reference; otherwise FA (`unconfirmed` counted separately). Own exec cache under `out/analysis/v54_sonnet_mutconcept`.

## Report (per task and arm)
Valid programs (and invalid reasons), tests, confirmed (0/1), true tests, FA tests, consensus, and the mechanism count:
valid programs that differ from the PUT on ≥ 1 question input (0 for every program = common-mode). Arms: Sonnet `tc`,
Sonnet `tc_concept`; Qwen v46 `tc`/`tc_concept` first 3 programs (k-matched) and all 10, same tasks.
Concept effect = Sonnet `tc_concept` vs Sonnet `tc`. A difference of 1–2 tasks out of 6 is not evidence; a concept
signal worth a registered follow-up needs `tc_concept` ≥ `tc` + 2 confirmed tasks with FA tests ≤ `tc`.

## Caveats (stated before results)
Sonnet has likely seen these LeetCode problems; a win may be recall, not the concept. The TC variant template asks for
a repaired implementation, so a strong writer may simply repair the bug (oracle = repair), with or without concepts.

## Amendment 1 (2026-10-24, after an independent read-only review and a 1-subagent smoke; before any scored call)
The smoke (`out/.../smoke/tc/85/0.txt`, not scored) showed the transcript records Read, Write and `SubagentHandback`;
model `claude-sonnet-5-5`.
- Exclusion from the transcript, not a tool count: `audit` keeps a program only if the subagent's tool calls are
  exactly one Read of its prompt file and one Write of its answer file (the hand-back aside). `runs.json` stores the
  tool names, paths and models. A program missing from `runs.json` makes `score` fail.
- Spawn wording is neutral: read the prompt file, answer exactly as asked, write the reply verbatim. Do not read any
  other file (memory, AGENTS.md included), do not run code. Agent type `general-purpose`, `model: sonnet`.
- Order: `score` covers the Sonnet arms only. The Qwen k = 3 / k = 10 arms (`qwen`) run only after the registered v46
  `score` exists, so v54 does not reveal v46 early. `qwen` also checks that k = 10 matches v46 per task.
- Added: consensus tests (and FA); `score.json`/`qwen.json` written once (immutable).
- Secondary, program level: valid programs equal to the reference on every exposing question input, out of 18 per arm.
- Mechanism (approximate): programs containing a shown concept line with its edit applied (`tc` = base rate); per task,
  whether a D1 edit is among the ≤ 5 shown concepts (tasks 46, 65, 161 have more distinct edits than 5).
- Signal threshold reworded: a concept signal worth a registered follow-up needs `tc_concept` ≥ `tc` + 3 confirmed tasks,
  or ≥ 6 more right programs (secondary), with FA tests ≤ `tc`. Smaller differences are reported, not interpreted.
- Stated deviations from v46: the system message arrives inside a file, under Claude Code's own system prompt; no
  temperature/top_p/max_tokens control; invalid reason `empty` is classified first (v46 counts empty separately).

## Amendment 2 (2026-10-24, after the 36 subagents and `audit`, before any score/execution)
`audit` found 32/36 programs clean under Amendment 1; the other 4 only re-wrote their own answer file (tc/85/2,
tc/161/0, tc_concept/85/1: a second Write; tc/161/2: Write + 2 Edits). No subagent read or wrote any other file. The
strict rule would drop 3 `tc` programs and 1 `tc_concept` program, unbalancing the arms for a reason unrelated to
leakage. Primary rule from now on (leakage): one Read of its own prompt file first, then only Write/Edit of its own
answer file (the final file is the program). The Amendment 1 rule is kept as a sensitivity arm (`*_strict`, excluded
programs count as empty). No program content or outcome was looked at for this decision.

# v39 spec-alternative gate on vibepass_half — results, 2026-10-21

Output: `out/analysis/v39_specalt_vibepass/gate.json`. Rule: PREREG.md (4b4bc42) + Amendment 1 (f2f79e3, fd1ee81).

## Final (after the Amendment 1 retry)
- Calls: all 140 transport failures retried once when the endpoint returned (12:2x): 140/140 `stop`. Total 240/240
  programs, 79.6k completion tokens, no `length` cut-offs.
- Scoring note: the first `score` after the retry crashed (KeyError) because `ft_run.execute` reuses a cached
  `result.json` per directory, and the first-pass cache had no programs for the retried questions. The first-pass cache
  was moved to `cases_firstpass/` (kept) and everything was executed again from scratch. No code change.
- Valid programs (equal to the PUT on the public inputs): 84/330 program-task pairs; 15/24 questions have >= 1 valid
  program; 23/33 tasks have fewer than 3. Invalid programs run normally (342 ok / 12 exception / 9 timeout first
  results) and simply give wrong answers on the public examples: a model failure, not a harness failure.
- **C' = 12/33, H' = 2/33** (tasks 73, 74: same question 3655, one valid program each).
- Consensus witness tasks 3 (101, 121, 131); consensus precision 37/48 = 0.77 (false consensus: task 89 on 7 inputs,
  task 131 on 4).
- Correct-program share (descriptive, Amendment 1.2): question id < 3300: 30/39 valid programs correct (9 tasks);
  id >= 3300: 24/45 (24 tasks). Newer problems are solved much less often.

**Verdict (amended rule): no-go, G1 fails (12 < 17).** G2 also fails (2 < 3). The script still
prints "untestable (memorized)" because it implements the original rule; Amendment 1.2 dropped that condition before
this run, so the amended verdict above is the registered one.

Interpretation: on non-HumanEval tasks, Qwen-32B spec programs are too often wrong to serve as the second version
(no valid program for 9/24 questions), and where they are right the v31 templates have almost always exposed the bug
already (H' 2, from one question). Where >= 3 programs agree against the PUT, 23% of those inputs are false alarms.
The planned Mokav-style DET-search run between PUT and spec programs is **not** run (the v40 number is now used by another session for `pipelines/v40_concept_agent`). The paper route (Mokav over mutants v37,
spec programs on HumanEval v38, spec programs on VibePass v39) is closed; the bottleneck stays input reach (step b).

## First pass (transport-incomplete), 2026-10-21 00:40

Output: `out/analysis/v39_specalt_vibepass/gate_firstpass.json`, execution cache `cases_firstpass/`. Rule: PREREG.md (4b4bc42) + Amendment 1.

- Calls: 100/240 returned; the endpoint went offline at ~23:58 (121 NotFound, 11 server errors, 8 timeouts).
  Programs exist for 12/24 questions (ids 2839–3638, older problems); 0 for all questions with id >= 3655.
- Valid programs (equal to the PUT on the public inputs): 44 in total; 28/33 tasks have fewer than 3 valid programs.
  Many complete answers fail the public examples (e.g. q3211: 10 programs, 0 valid).
- C' (a valid program equals silver on an exposing input): **5/33**; H' (C' and no template exposure): **0/33**.
  Consensus witnesses 2 tasks (101, 121); consensus precision 35/42 = 0.83 (task 89: 4 valid programs agree on a wrong
  answer on 7 inputs → would be false alarms).
- Correct-program share 35/44; all from question ids < 3700, so not separable from memorization (Amendment 1.2).

Status: **incomplete**. Even on the 12 questions that returned, every task where a spec program witnesses the bug is a
task the v31 template pool already exposes (H' = 0). G1 (C' >= 17/33) cannot be reached unless the 12 missing
questions (21 tasks) almost all succeed. Retry of the 140 transport failures waits for the endpoint.

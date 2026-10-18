# v21_flowtools results — 2026-10-18 (Qwen2.5-Coder-7B, K=1, temperature 0)

Plan: `PLAN_FLOW_HYPOTHESIS_TOOLS.md`. Code: `pipelines/v21_flowtools/` (`flow_run.py`). PREREG: amendments 1–3
in `pipelines/v21_flowtools/PREREG.md`, all committed before the outputs they govern. Raw/frozen outputs:
`out/pipelines/v21_flowtools/humaneval/flowrun/{diag16,pilot20}/` (`protocol.json`, `generation_frozen.json`,
`score.json`). Superseded attempts kept as `*_attempt{1..4}_*` (format/bug/operational failures, see PREREG).

Definitions: confirmed detection = admissible input, PUT output ≠ reference, model expected == reference.
False alarm = expected ≠ PUT output while PUT == reference. "beyond W" = confirmed on a task where the
witness-only pool showed no PUT/reference discrepancy. Each LLM arm = 3 calls (2 rounds + final), ≤6 final tests.

## diag16 (controlled fixtures, 7 buggy; f13 unscored)

Shared stages: concept/behavior/hypothesis schema-valid 16/16; 8 cases got mismatch hypotheses.

| arm | tasks confirmed | false alarms (tasks) | admissible tests | tokens in/out |
|---|---|---|---|---|
| concept+hyp | 5 | 3 (2) | 85 | 99.6k/15.3k |
| input+hyp | 6 | 6 (3) | 64 | 107.5k/15.4k |
| concept+input+hyp | 7 | 11 (4) | 78 | 109.3k/15.3k |
| agent-tools | 5 | 4 (4) | 83 | 61.0k/6.0k |
| fixed-tools | 5 | 9 (5) | 77 | 109.8k/15.5k |
| flow+input | 6 | 2 (1) | 81 | 103.3k/15.8k |
| toolinput | 7 | 4 (2) | 78 | 86.9k/15.8k |
| plain | 6 | 8 (3) | 73 | 78.3k/15.7k |
| placebo+input | 5 | 4 (2) | 81 | 89.9k/15.1k |
| witness-only | 0 (base inputs only) | 0 | 16 | 0 |

Ceiling effect: toolinput and concept+input+hyp both 7/7, concept+input+hyp with more false alarms.

## pilot20 (v7 pilot tasks, HumanEval+ canonical reference)

Shared stages: concept 20/20, behavior 18/20, hypothesis 19/20 valid; 19 tasks with ≥1 mismatch hypothesis.
Witness-only: frozen v7 fuzz witnesses already show a PUT/reference discrepancy on 8/20 tasks (no expected
value, so never a confirmed detection).

| arm | tasks confirmed | beyond W | discrepancy tasks | false alarms (tasks) | schema errors | tokens in/out |
|---|---|---|---|---|---|---|
| concept+hyp | 3 | 1 | 7 | 28 (9) | 2 | 203.6k/20.1k |
| input+hyp | 2 | 1 | 5 | 19 (6) | 6 | 220.4k/20.4k |
| concept+input+hyp | 2 | 1 | 5 | 21 (6) | 3 | 232.9k/21.9k |
| agent-tools | 4 | 2 | 8 | 23 (9) | 2 | 155.5k/9.5k |
| fixed-tools | 3 | 3 | 8 | 23 (10) | 2 | 237.9k/20.9k |
| flow+input | 4 | 1 | 8 | 32 (11) | 3 | 212.9k/22.1k |
| toolinput | 3 | 1 | 7 | 34 (9) | 4 | 159.4k/23.1k |
| plain | 2 | 1 | 7 | 33 (10) | 4 | 146.5k/21.9k |
| placebo+input | 1 | 0 | 5 | 38 (11) | 3 | 165.1k/21.8k |

Paired task detection (wins/losses): concept+input+hyp vs toolinput 1/2, vs plain 1/1, vs placebo+input 2/1;
concept+hyp vs plain 2/1; agent-tools vs fixed-tools 2/1; input+hyp vs toolinput 1/2.

## Verdict (by the amendment-1 rule)

No concept arm beats toolinput AND plain AND placebo+input with no more false alarms → **negative /
inconclusive**. The bottleneck is the expected value: many discrepancy tasks have a wrong expected
(`discrepancy_wrong_expected` 7–14 per arm) and false alarms dominate confirmed detections on pilot20.
agent-tools (4 tasks, fewest tokens) and fixed-tools (3 beyond W) are the only arms above toolinput on
some count, but by ≤1–2 tasks at n=20, K=1 — no claim. Tool mechanics worked (0 invalid inputs on diag16
after the arm-neutral normalization; agent-tools used 35–40 actions with few errors). No human semantic
adjudication of hypotheses was done; no promotion over v7.

# v29_vibepass: Codex full pipeline on VibePass (held-out, one shot)

> **INVALID (2026-10-19).** The prompt-visible `base_tests` came from `humaneval_mbpp_plus.jsonl` `test`, which embeds the
> canonical solution, the contract and all hidden inputs (1848/1980 requests). The model saw the reference, so none of the
> numbers below measure the method. Kept for the record only; fixed in v31 (public asserts from `humaneval_mbpp.jsonl`).

Date 2026-10-19. Pipeline `pipelines/v29_vibepass/` (frozen v28 config + VibePass adapter; PREREG v29 + amendment 1,
transport only). Model: Codex `gpt-5.6-luna`, reasoning low, all tools disabled (657/657 recorded completions have
`tool_executions = 0`). 66 VibePass PUTs (24 LeetCode questions, every PUT is buggy but passes the public tests).
Score: `out/pipelines/v29_vibepass/humaneval/flowrun/codex/vibepass/score.json`. 660/660 arm jobs, 0 failures.

Shared stages: concept valid 66/66, behavior 50, hypothesis 34, CFG supported 39/66.

| arm | confirmed tasks /66 | discovered (PUT≠ref on admissible input) | false alarms (inputs/tasks) | contract-invalid inputs | wrong expected |
|---|---|---|---|---|---|
| concept+input+hyp | **9** | 9 | 5 / 3 | 1 | 3 |
| flow+input | 8 | 8 | 3 / 3 | 0 | 2 |
| toolinput | 8 | 9 | **1 / 1** | 1 | 4 |
| plain | 7 | 7 | 4 / 4 | 1 | 5 |
| concept+hyp | 6 | 8 | 2 / 2 | 8 | 2 |
| agent-tools | 6 | 7 | 5 / 5 | 0 | 2 |
| fixed-tools | 6 | 7 | 6 / 6 | 0 | 2 |
| placebo+input | 6 | 8 | 6 / 6 | 1 | 5 |
| input+hyp | 5 | 7 | 3 / 2 | 7 | 6 |
| witness-only | 0 | 0 | 0 | 0 | 0 |

Paired task detection: concept+input+hyp vs toolinput 1–0, vs plain 3–1, vs placebo+input 3–0, vs input+hyp 4–0;
concept+hyp vs plain 2–3; agent-tools vs fixed-tools 1–1. Union over arms: 10/66 tasks (71, 87, 120, 121, 160–165).

## Decision rule (v21 amendment 1)
concept+input+hyp beats toolinput, plain and placebo+input on paired detection, but has more false alarms than
toolinput (5 vs 1) and plain (5 vs 4) → **rule not passed**. Wins are 1–3 tasks at n=66, K=1: descriptive only.

## Reading
- Bottleneck moved from oracle (Qwen) to **input**: Codex's expected values are rarely wrong (2–6 inputs per arm),
  but only 7–9/66 tasks get an admissible input where PUT ≠ silver. VibePass bugs are hidden-test failures that
  public base inputs never expose (witness-only 0/66).
- No ceiling here (unlike HumanEval v28: 16–17/20), so the benchmark can separate arms; the concept arms are at the
  top but the margin is within noise and costs false alarms.
- Concept-only (concept+hyp, input+hyp) produce many contract-invalid inputs (7–8); arms that see concrete inputs/flow
  produce ~0–1. Concepts without grounding push the model outside the input contract.
- Caveat: the 10 detected tasks come from only 5 of 24 questions (3655 ×3, 3686 ×2, 3699 ×2, 3026 ×2, 2952 ×1), so effective n is smaller.

Not promoted. Next lever: input generation (more discovery budget / contract-aware fuzz witnesses), not oracle.

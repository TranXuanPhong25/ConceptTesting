# v28_codexflow results — 2026-10-18 (Codex gpt-5.6-luna, reasoning low, tools disabled, K=1)

PREREG: `pipelines/v28_codexflow/PREREG.md` (committed before outputs). Codex ran with shell/code-mode/browser/
computer-use/apps disabled; 0 tool executions recorded in every response. Operational note (one 3× timeout call
recorded as arm error, resumed without source change) in the folder CHANGELOG.

## 1. Full pipeline (v21_flowtools flow_run) on pilot20 — Codex vs Qwen

| arm | Codex: tasks confirmed | beyond W | false alarms (tasks) | Qwen (v21): confirmed | Qwen FA |
|---|---|---|---|---|---|
| concept+hyp | **17** | 9 | 2 (2) | 3 | 28 |
| input+hyp | 16 | 9 | 1 (1) | 2 | 19 |
| concept+input+hyp | 16 | 8 | 3 (2) | 2 | 21 |
| agent-tools | 16 | 9 | 2 (1) | 4 | 23 |
| fixed-tools | 16 | 8 | 0 (0) | 3 | 23 |
| flow+input | **17** | 9 | 2 (2) | 4 | 32 |
| toolinput | **17** | 9 | 1 (1) | 3 | 34 |
| plain | 16 | 9 | 2 (2) | 2 | 33 |
| placebo+input | 16 | 9 | 2 (1) | 1 | 38 |
| witness-only | 0 (8 discrepancy tasks) | – | 0 | 0 | 0 |

Shared stages valid: concept 20/20, behavior 20/20, hypothesis 19/20; 14 tasks with a mismatch hypothesis.
Paired: concept+input+hyp vs toolinput 0/1, vs plain 1/1, vs placebo+input 1/1; concept+hyp vs plain 1/0.

**Reading:** with Codex every arm confirms 16–17/20 tasks with 0–3 false alarms (Qwen: 1–4 tasks, 19–38 FA).
The stronger model removes the oracle bottleneck, but all arms — including plain — hit the same ceiling, so
concept/hypothesis/tool guidance shows **no added value** on pilot20 (decision rule not met). HumanEval
memorization by Codex is a plausible contributor to the ceiling.

## 2. Oracle cells without tools (v27 recheck; pilot20 precision TP/FA)

| oracle | Qwen | Codex+tools orig | Codex no-tools orig | Codex+tools strict | Codex no-tools strict |
|---|---|---|---|---|---|
| exact_spec | 0.21 | 0.76 | 0.84 | 0.90 | 0.84 |
| exact_code | 0.20 | 0.47 | 0.59 | 0.76 | 0.68 |
| property | 0.15 | 0.34 | 0.40 | 1.00 | **1.00** (10/0) |
| metamorphic | 0.18 | 1.00 | 0.78 | 1.00 | 0.73 |

diag16 no-tools: exact 0.94–1.00, property strict 1.00, metamorphic 0.79–1.00. The v27 conclusion holds without code
execution: the oracle failure is model-limited; strict rules make the property oracle sound for a capable model.

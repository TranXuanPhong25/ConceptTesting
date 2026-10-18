# v27_codexoracle results — 2026-10-18: model vs prompt as cause of the oracle failure

Design (PREREG in `pipelines/v27_codexoracle/PREREG.md`, committed before outputs): 2×2 model {Qwen2.5-Coder-7B,
Codex CLI gpt-5.6-luna reasoning=low} × prompt {original v26, strict = + rules against the v26 failure modes}.
Same fixed pools, arms, sandbox and post-freeze scoring as v26. qwen×original = frozen v26 result. K=1.
Outputs: `out/pipelines/v27_codexoracle/humaneval/oracle/<model>_<variant>/<cohort>/score.json`.

## pilot20 (22 discrepancy inputs on 10 tasks) — precision (TP / FA), tasks confirmed

| oracle | qwen original | qwen strict | codex original | codex strict |
|---|---|---|---|---|
| exact_spec | 0.21 (13/48), 8 | 0.22 (13/47), 8 | 0.76 (19/6), 9 | **0.90 (17/2), 8** |
| exact_code | 0.20 (13/53), 8 | 0.18 (11/52), 9 | 0.47 (15/17), 7 | 0.76 (19/6), 8 |
| property | 0.15 (16/92), 6 | 0.14 (4/24), 2 | 0.34 (16/31), 9 | **1.00 (15/0), 8** |
| metamorphic | 0.18 (17/78), 4 | 0.15 (10/55), 4 | 1.00 (38/0), 6 | 1.00 (21/0), 4 |
| consensus exact_code ∧ property | 0.24, 4 | 0.08, 1 | 1.00 (11/0), 6 | 1.00 (13/0), 7 |
| properties failing on reference output | 134/699 (+120 err) | 33/699 (+295 err) | 31/651 | **0/699** |

## diag16 (authored fixtures, unlikely to be memorized; 31 discrepancy inputs on 7 cases)

| oracle | qwen original | qwen strict | codex original | codex strict |
|---|---|---|---|---|
| exact_spec | 0.47 | 0.47 | 0.86 | 0.86 |
| exact_code | 0.43 | 0.41 | 0.97 | 0.97 |
| property | 0.31 | 0.27 | 0.46 | **0.79** |
| metamorphic | 0.23 | 0.45 | 1.00 | 1.00 |
| properties failing on reference output | 85/501 | 175/501 | 53/501 | 5/471 |

## Reading (registered rule)

- **Model-limited: yes.** At the same prompt, Codex beats Qwen on every oracle (pilot20 exact_spec 0.21 → 0.76,
  property 0.15 → 0.34, metamorphic 0.18 → 1.00; diag16 similar).
- **Prompt-limited: yes, but only for a capable model.** Strict rules turn Codex properties from 0.34 to 1.00 precision
  (31 → 0 unsound property checks) and exact_code 0.47 → 0.76. For Qwen the same rules do not help: fewer unsound
  checks on pilot20 but 295 crashes and recall collapses (property TP 16 → 4); on diag16 soundness gets worse.
- With codex×strict, the concept-as-property oracle has **zero false alarms** and confirms 8/10 discrepancy tasks
  on pilot20 (exact_spec: 8 tasks, 2 FA). Metamorphic is precise but misses many (15 missed).

Caveats: Codex is a far larger hosted model; HumanEval may be memorized (pilot20) — diag16 fixtures are novel and show
the same direction. n=20/16, K=1, one reasoning setting. Not a pipeline promotion; it localizes the failure: Qwen 7B
cannot reliably write correct oracles, and a precise prompt matters once the model can follow it.

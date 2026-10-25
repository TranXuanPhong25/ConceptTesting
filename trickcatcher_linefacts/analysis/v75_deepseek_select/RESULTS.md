# v75 results: DeepSeek-V4-Flash (relace/fp4) picks concept instances (v47 replay)

Source: `out/analysis/v75_deepseek_select/score.json` (v47 scorer unchanged). Attempt 2 (amendment 1): 66/66 calls,
all Relace, prompts sha256-identical to v47. Cost attempt 2 **$0.125393** (123,306 input + 710,485 output, 624,847
reasoning); attempt 1 $0.0457 + probes ≈ $0.0096 → total ≈ $0.18. **28/66 finish=length with empty content**
even with `reasoning.max_tokens=4096` and max_tokens 16384: the provider does not enforce the reasoning budget and the
model hand-enumerates examples until the cap. Empty answers count as not covered (PREREG).

| arm | parsed | covered@3 | random3 | first3 | kind-matched random | perfect |
|---|---|---|---|---|---|---|
| spec+code | 15/33 | **10** | 18.25 | 18 | 9.60 | 23 |
| spec-only | 23/33 | **12** | 17.96 | 18 | 12.97 | 22 |

**Verdict: no-go.** Exploratory, on the tasks where DeepSeek answered: spec+code (n=15) DeepSeek 10 vs random3 9.43,
first3 9, GPT-OSS 8, Qwen 8; spec-only (n=23) 12 vs random3 13.68, first3 13, GPT-OSS 11, Qwen 12. Even conditioned
on answering, DeepSeek is at random level (the parsed subset is self-selected: easier tasks finish).

## Reading
Third model, same result: Qwen-32B, GPT-OSS-120B and DeepSeek-V4-Flash all pick at or below random. Reasoning models
spend their budget trying to solve the task by hand instead of using the menu; the menu text carries no signal that
separates bug-revealing instances.

## Amendment 2 result (28 empty calls re-called with max_tokens 65536) — final
`score.json` (attempt-2 score kept as `score_attempt2.json`). Re-calls: 19 stop, 9 still length at 65,536 tokens
(spec+code 48, 66, 69, 73, 74, 164, 168, 171; spec-only 36), $0.145. Total v75 spend ≈ $0.33.

| arm | parsed | covered@3 | random3 | p | first3 | kind-matched random | perfect |
|---|---|---|---|---|---|---|---|
| spec+code | 25/33 | **17** | 18.25 | 0.88 | 18 | 15.35 | 23 |
| spec-only | 32/33 | **15** | 17.96 | 0.99 | 18 | 15.89 | 22 |

**Verdict unchanged: no-go.** Exploratory parsed subset: spec+code (n=25) DeepSeek 17 vs random3 16.25, first3 16,
GPT-OSS 13, Qwen 14; spec-only (n=32) 15 vs 16.97, first3 17, GPT-OSS 13, Qwen 14. DeepSeek is the best of the three
models on the same tasks (+3/+4 vs Qwen with code) but still ≈ random and ≤ first3. Still-empty calls are mostly
v44-unreachable tasks (48, 69, 73, 74, 168, 171).

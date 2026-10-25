# v74 results: GPT-OSS-120B picks concept instances (v47 replay)

Source: `out/analysis/v74_oss_select/score.json` (frozen; v47 scorer unchanged). 66/66 calls, all served by Near AI
(OpenRouter price sort), prompts sha256-identical to v47 on all 66. Cost **$0.015635** (126,058 input + 80,987 output
tokens, of which 67,692 reasoning). 65 finish=stop; case 61 spec+code finish=length (4096 tokens all reasoning, empty
answer → 0 picks, counted as not covered per PREREG; random3 there is 0.9999, so at most +1).

| arm | model | covered@3 | random3 | p vs random3 | first3 | kind-matched random | perfect menu |
|---|---|---|---|---|---|---|---|
| spec+code | GPT-OSS-120B | **15** | 18.25 | 0.99 | 18 | 15.77 | 23 |
| spec+code | Qwen2.5-Coder-32B (v47) | 16 | 18.25 | 0.96 | 18 | 17.06 | 23 |
| spec-only | GPT-OSS-120B | **14** | 17.96 | 1.00 | 18 | 16.09 | 22 |
| spec-only | Qwen2.5-Coder-32B (v47) | 15 | 17.96 | 0.99 | 18 | 15.66 | 22 |

**Verdict: no-go** (rule: ≥ random3 + 3 and ≥ 0.5 × perfect). Even crediting case 61, spec+code = 16 = Qwen.

Per task vs Qwen (spec+code): 13 tasks both, GPT-OSS-only {65, 103}, Qwen-only {61, 75, 77}. spec-only: 13 both,
GPT-OSS-only {103}, Qwen-only {46, 75}.

Pick kinds, spec+code: class 50, coverage 24, boundary 12, spec_range 8, mutation 2 (Qwen picked class+boundary
mostly). The stronger model shifts toward code paths but still lands at kind-matched random.

## Reading
A ~4× larger reasoning model does not fix concept-instance selection: both models sit below uniform random and below
"take the first 3". So the v47 failure is not a Qwen-size limit. With these one-line menu descriptions the LLM has no
information that separates bug-revealing instances from others; the menu, not the choice, carries the coverage.

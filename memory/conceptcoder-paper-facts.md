---
name: conceptcoder-paper-facts
description: ConceptCoder (arXiv 2603.23470) full-PDF facts — gain comes from concept-supervised training; non-vuln concepts keep ~3/4 of it; concept prompting (A.4) hurts GPT-5.2
metadata:
  node_type: memory
  type: reference
  originSessionId: 7ff5ccb6-c822-4e0c-85b2-728de325d857
  modified: 2026-10-09T18:51:55.212Z
---

ConceptCoder (Rahman, Tong, Le; Iowa State; arXiv 2603.23470v1, 2026-03-24). Full PDF read 2026-10-10.

- Method: statement-level multi-hot concept labels computed by tools. VD has 7 static concepts from 4 CWE families. BP has 12 abstract values from TRACED traces (zero / pos-regular / pos-large / neg-regular / neg-large, True/False, NULL, alphabetic, initialized). Multi-task: concept head (BCE) + task head. VD uses the sequential bottleneck; BP uses the parallel setting.
- Headline VD F1 (9 models ≤ 8B): concept dataset 66.32 → 72.15 as stated, general 55.11 → 58.52, BP 85.27 → 86.50. Best: QN-7B 74.76 / 60.6.
- The stated concept-dataset averages don't recompute from the per-model numbers (66.13 → 72.4). MC-7B is 72.25 in Fig. 3a but 72.75 in Table 6. The intro swaps the GPT-5.2 and Claude numbers relative to Table 4.
- Table 6 non-vulnerable concepts recover about 3/4 of the gain (74% on the concept dataset, 77% on general), so much of the effect is the auxiliary-supervision format.
- Datasets: "concept" = 28,974 functions of the 4 CWE families the concepts come from (released test split 16.67% vulnerable, so predicting all-vulnerable gives F1 28.57); "general" = 80,204 functions, 134 CWEs, both from PrimeVul + DiverseVul. The general vulnerable ratio is not stated.
- Appendix A.4, concept prompting vs zero-shot CoT (concept / general): GPT-5.2 46.58 / 37.33 → 32.35 / 28.12; Claude Opus 4.5 48.57 / 42.10 → 47.22 / 41.26.
  - The paper itself only says hierarchical prompting "does not help enough". The drop is my comparison of Table 8 against Table 4. The paper doesn't confirm identical test sets or settings, and its text calls Table 8 "Figure 8".
  - Under either GPT/Claude assignment of the swapped intro numbers: GPT-5.2 is 14–16 points lower, Claude is within ±1.4 (flat).
- Generalization averages +1.3 F1. Robustness (NatGen) goes 18.3 → 26.3.
- The released code has 8 labels (adds if_statement) and crude rules ("alloc" / "free" in the callee name).

**Why:** the thesis builds on ConceptCoder, and prompt-time concepts keep failing in this repo.

**How to apply:** when someone proposes prompt-time concepts, cite A.4 and the non-vulnerable-concept result. The transferable parts are a fixed human-designed vocabulary, tool-computed labels, and an intermediate abstraction level. Related: [[thesis-concept-requirement]], [[hybrid-c1-verdict]].

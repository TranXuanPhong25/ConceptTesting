# v47 results: can the LLM pick the right concept instance? (Qwen2.5-Coder-32B, vibepass_half, 33 PUTs)

Source: `out/analysis/v47_concept_select/score.json` (frozen; 66/66 calls, all finish=stop, 33/33 parsed per arm,
0 errors, 0 skipped generated inputs). PREREG: `PREREG.md` (amendments 1–2; amendment 2 is transport only).

## Part B (registered): pick 3 instances from a frozen menu
Rule: promising iff covered@3 ≥ random3 + 3 AND covered@3 ≥ 0.5 × perfect_menu.

| arm | covered@3 | random3 | p vs random3 | first3 | per-kind random3 | kind-matched random | perfect menu |
|---|---|---|---|---|---|---|---|
| spec+code | 16 | 18.25 | 0.96 | 18 | 19.07 | 17.06 | 23 |
| spec-only | 15 | 17.96 | 0.99 | 18 | 17.02 | 15.66 | 22 |

**Verdict: no-go.** The model's picks are *below* a uniform random 3 from the same menu and below simply taking the
first 3 items. Kind-matched random (random instances of the kinds it chose) is ≈ the model (17.06 vs 16; 15.66 vs
15), so the model does not choose the right instance within a kind, and its kind preference (class, boundary) is not
better than the menu mix either. Code access adds 1 task. Spec-only picks are 92/99 class+boundary.

## Part A (exploratory): two new tool methods
- union of the 4 v44 input kinds 21 (= v44, reproduced 33/33); with spec_range + value_biased union6 = 23; c1 23 (v44: 22).
- spec_range ideal 11 vs matched random 10.41; value_biased 12 vs 11.96: no concentration beyond random over the reach set.
- New tasks reached: 56 (value_biased, one of the v45 "repeated special values" group) and 89. The other 10 of the 11
  unreachable tasks stay unreachable; 48/73/74/168 (large values) are not reached by spec_range.

## Reading
Concept accuracy was the hypothesised lever (v44: a perfect pick doubles coverage). With frozen menus where a perfect
pick reaches 22–23/33, the LLM reaches 15–16, below random. Signal: negative for LLM instance selection from
tool-generated menus at this model size; the menu itself, not the selection, carries the coverage.

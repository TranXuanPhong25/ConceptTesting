---
name: v51-latent-concept
description: 2026-10-23 v51 frozen Qwen-1.5B hidden-state probes + discrepancy-concept bottleneck as per-input oracle on VibePass — NO-GO; intrinsic NLL .65 beats all probes
metadata:
  type: project
---

v51 (`trickcatcher_linefacts/analysis/v51_latent_concept/`), CPU, $0. User approved the direction ("đồng ý") after
[[latent-concept-oracle-proposal]].

- **Setup:** probes on Qwen2.5-Coder-1.5B residuals (layer 28 chosen), trained on MBPP+ canonical-vs-mutmut outputs
  (value only, 13,810 rows). Eval: v41 VibePass pool, 22 PUTs, 17 problems.
- **MBPP+ validation:** direct .626, CBM .627, type-matched placebo .631. Concepts add nothing even in-distribution.
- **VibePass macro AUC:** direct .476, CBM .495, placebo .385, verbal .441, surface .496, intrinsic NLL .650 (direct
  loses to intrinsic 3/14, p = .013). Decision: **NO-GO**.
- **Mechanism:**
  - VibePass wrong outputs: 52% NUM_NEAR, 0 TYPE/BOOL/SIZE. The probes read output-form concepts well (≥ .92) but
    NUM_NEAR only .78. Concept top-1 accuracy is 19%.
  - VibePass specs are about 10× longer than MBPP+.
  - B − C passes only because the placebo is below chance.
- **Top-3:** the logged top-3 has a tie artifact (eval rows are ordered exposing-first); surface 16 → 9.2
  tie-random. Every arm is ≤ the random 11.7/22.

**Why:** closes the latent-readout route. An off-by-small-number bug needs the model to solve the task, and a residual
readout does not do that.

**How to apply:**
- Do not propose 7B or larger MBPP+ training for this route (see [[signal-not-more-data]]).
- Intrinsic NLL is concept-free, so it can only be a selector inside a concept method (see
  [[thesis-concept-requirement]]).
- When ranking rows, break ties randomly.

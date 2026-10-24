---
name: v53-validity-smallscope
description: 2026-10-24 validity scoring complete: concept=lines=open on all fixed-universe inputs; taxonomy not promising, extraction removes invalid-input FA
metadata:
  type: project
---

2026-10-24 user authorized execution of PLAN_CONCEPT_MECHANISM_20261024 ("làm đi"). Completed existing v53 validity evaluation after independent source/transcript review, original CPU scoring with integrity guards, and independent postscore verification. No new model calls, no changed answers/source/gates. This v53 validity experiment is distinct from [[v53-sonnet-tester]].

Original registered primary result: **not promising**, concept-open recall margin0 vs required+.10. All safety gates pass. Concept/lines/open acceptance masks are identical on all32,311task-input rows; catch12,842invalid, reject0of19,469valid and0of4,084exposing. Numeric tool catches1,854invalid (14.44%); it already uses repaired v48 menu_fixed, not old v44 parser. Sonnet FA56→0, Qwen145→108 in every model-filter arm;0confirmed task gained/lost. Extra confirmed tests are cap20refill, not new tasks/inputs.

**Why:** validity extraction has useful engineering value on this dev universe, but typed taxonomy adds no measured advantage over open or untyped extraction. Perfect finite-pool agreement is not universal validator soundness. **How to apply:** retain original NO-GO and report-only concept-lines comparison. The registered fallback uses open rather than numeric tool; Stage2 remains unregistered/unlaunched and cannot be called concept-guided generation evidence. Reports: `analysis/v53_validity_smallscope/RESULTS.md`, `analysis/concept_mechanism_20261024/`. Held-out unchanged; no larger run to rescue taxonomy.

**Stage 2 (2026-10-24, Claude; PREREG_STAGE2 + self-review because Codex quota was out).** Sonnet `defn` k=3 oracle + `open` filter, 33 tasks. Confirmed tasks: scope (concept: DIMENSION scopes, exhaustive ≤300) **18**, plain Sonnet generator **24** (prec .96), typed tool 17, random_small 21, universe 22, universe∪plain 24. Registered verdict **not promising** (scope − plain = −6). Mechanism: exhaustiveness within 300 inputs shrinks sizes to ≤6, but bugs on 61/65/66/77 need size 7–10; the 168/171 reach comes from LLM generation, not from the concept; the remaining FA (161 family) are common-mode Sonnet oracle errors on valid inputs; 141 is abstention. **How to apply:** a strong-writer pipeline (Sonnet defn + filter + plain inputs) reaches 24/33. Do not retry small-scope or enumeration concepts on inputs. Open problems for a fresh cohort: common-mode oracle errors and abstention. `analysis/v53_validity_smallscope/RESULTS_STAGE2.md`.

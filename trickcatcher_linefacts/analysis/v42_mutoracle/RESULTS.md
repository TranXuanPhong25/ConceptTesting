# v42 mutant-disagreement oracle questions — CPU ceiling results (2026-10-21)

Output `out/analysis/v42_mutoracle/ceiling.json` (+ `packages.json`). Rule: PREREG.md (613e86b) + Amendment 1 after an
independent read-only review (2ea21dd), both before any reference/exposure was computed.

| measure (vibepass_half, 33 PUTs, v41 pool × v34 surviving mutants) | value |
|---|---|
| C1 (pool exposes, = v41) | 22/33 |
| **D1**: package has a question on a confirmed exposing input whose mutant output = reference | **15/33** (uncapped, whole pool: 19) |
| D2: package has a confirmed exposing input | 15/33 vs E[random-k] 13.32 |
| median per-task lift (C1 tasks; empty package = 0) | **0.62** |
| package questions on contract-valid inputs: mutant right / PUT right / neither | **52 / 335 / 46** |
| mutants run / collapsed (identical outcome vectors) / unusable / with skipped calls | 1771 / 1271 / 2 / 8 |
| package validity share; batch vs official agreement | 0.71; 996/996 |

**Verdict by the registered rule: no-go** (D1 15 < 17, median lift 0.62 < 2; D2 > random-k holds, 15 > 13.3).

## Reading
- Mutant disagreements select bug-revealing inputs only slightly better than random (lift 0.62 vs v41 relations 0.38);
  strong enrichment only in 101 (8.2), 163 (5.5), 65 (5.2), 46 (5.0), 141 (4.4), 161 (4.0), 61 (3.2).
- The binary question is usually answered by the PUT: on valid package inputs the mutant output is right in 12% of
  questions, the PUT in 77%. A binary judge needs specificity ≫ 0.9 to keep false alarms below true detections.
- 11 tasks have no bug in the pool (C1 false) yet get up to 32 questions, all PUT-right or invalid: pure false-alarm
  exposure. The remaining loss (19 → 15) is the 32-input cap / rarest-disagreement ordering.

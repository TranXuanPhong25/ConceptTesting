# v44 concept taxonomy × tool method matrix — results (2026-10-21)

Output `out/analysis/v44_concept_matrix/matrix.json` (+ `instances.json`). Rule: PREREG.md + Amendment 1 + re-review
note (80d36bb), all before the run; two independent read-only review passes (GO after fixes). 0 case/kind errors.

## Input-side kinds (best instance chosen with the reference = an accurate concept; ≤ 32 inputs shown)
| kind | applicable /33 | ideal coverage | matched random (k = reach) | random instance (no-skill pick) | median lift on C1 tasks | mean universe / reach |
|---|---|---|---|---|---|---|
| input class | 33 | 20 | 20.0 | 10.1 | 2.43 | 209 / 195 |
| boundary (spec constraints) | 31 | 14 | 13.9 | 6.6 | 2.10 | 143 / 132 |
| coverage arcs (coverage.py) | 23 | 9 | 10.5 | 7.0 | 1.30 | 2095 / 73 |
| surviving mutants (v42_mutoracle outcomes) | 31 | 19 | 18.6 | 14.5 | 2.57 | 2084 / 136 |
| **union of input kinds (gated)** | | **21** | **21.36** | | | reach 180–940 per task |

**Verdict by the registered rule: no-go** (union 21 < 22 and not ≥ matched random + 3). C1 stays 22/33: the
generated class/boundary inputs reach no task the v41 pool missed.

## Oracle kinds (tool-mined candidates, accuracy vs reference)
| kind | candidates (PUT holds ≥ 75%) | accurate (reference holds 100%) | false-alarm inputs from inaccurate ones | tasks where an accurate one flags a bug |
|---|---|---|---|---|
| metamorphic | 260 | 145 (56%) | 3877 | 3 |
| output property | 66 | 50 (76%) | 1251 | 1 |

## Reading (method, not dataset)
- **Tool coverage:** 11/33 tasks get no bug-revealing input from any of the six methods (6, 39, 48, 56, 58, 69, 70,
  73, 74, 168, 171). The methods all perturb small public-like inputs; none produces the structures these bugs need.
- **Concept accuracy matters, but alone is not enough:** with a perfect pick, one instance (≤ 32 inputs) reaches 20
  tasks (class) vs 10 for a random instance, 14 vs 6.6 (boundary), 19 vs 14.5 (mutants). Yet showing every instance's
  inputs equals random sampling of the same size: the kinds partition the space, they do not concentrate bugs.
- **Oracle concepts:** generic metamorphic relations / output properties are wrong 24–44% of the time when mined from
  PUT behaviour, produce thousands of false-alarm inputs, and even the accurate ones flag the bug in only 1–3 tasks:
  these bugs are not violations of generic relations.

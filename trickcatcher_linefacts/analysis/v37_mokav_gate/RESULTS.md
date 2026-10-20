# v37 Mokav gate — results (2026-10-20)

Output: `out/analysis/v37_mokav_gate/gate.json`. Rule in PREREG.md (committed cc28542 before computing).

| measure (pilot20, EvalPlus pool ≈ 300 inputs/task) | tasks |
|---|---|
| PUT ≠ canonical on the pool (exposed) | 18/20 |
| **C**: some surviving mutant equals canonical on an exposing input | **3/20** (0, 108, 116) |
| F: one survivor equals canonical on the whole pool (definition fixed, see below) | 1/20 (0) |
| **H**: C and the v31 template pool exposes nothing | **1/20** (0) |
| v31 template pool (public-domain filter) exposes PUT ≠ canonical | 9/20 |

**Verdict by the registered rule: G1 fails (3 < 10) and G2 fails (1 < 3) → no-go** for Mokav-style differential
search over surviving mutants.

- Why: HumanEval PUTs are short; mutmut gives 7–65 mutants and a median of 3 survivors per task (4 tasks have none).
  Survivors differ from the PUT on the pool in 15 tasks, but almost never in the direction of the canonical solution:
  the alternatives are other wrong programs, not candidate fixes. Single-edit mutants are not a fix space for these bugs.
- Post-hoc correction (descriptive only, no rule change): the script's `clean` flag also counted a survivor that times
  out on the exposing input (task 43, clean 1 but correcting 0). Requiring correcting as well gives F = 1, not 2.
- Consistent with v35 on VibePass (4/33 regression-free corrections) and with the fault-localization review.
- Next (as registered): replace mutant alternatives with spec-derived programs (CASCADE / TrickCatcher style), v38.

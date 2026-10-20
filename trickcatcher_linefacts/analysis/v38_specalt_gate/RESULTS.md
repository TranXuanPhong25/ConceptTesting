# v38 spec-alternative gate — results (2026-10-20)

Output: `out/analysis/v38_specalt_gate/gate.json`. Rule in PREREG.md (committed d264737 before computing).

| measure (pilot20, v37 EvalPlus pool) | value |
|---|---|
| C': a valid Qwen DPP program equals canonical on an exposing input | 18/20 (all 18 exposed tasks) |
| H': C' and the v31 template pool exposes nothing | 9/20 |
| consensus witness (>= 3 valid programs agree, != PUT, = canonical) | 18/20 |
| consensus DET precision (PUT wrong where consensus != PUT) | 804/804 = 1.0 |
| valid programs per task | 10 in 16 tasks, 8–9 in 2, 3 in 2 |

**Registered verdict: G1' and G2' pass → "go".** It is **not interpretable** as evidence for the method:

- Validity check (post-hoc, before any further step): **182 of the 183 valid DPP programs** equal the HumanEval+
  canonical solution on every completed pool input. Qwen2.5-Coder-7B has memorized HumanEval. The "alternative version" is the answer key, so the gate measures contamination.
- The same applies to the HumanEval/MBPP-based sets (dev113, pilot20, MBPP+ real-12): spec-derived alternatives
  cannot be evaluated there. (Correction 2026-10-20: VibePass is LeetCode / LiveCodeBench in HumanEval format, not
  HumanEval; it was wrongly listed here. v39 runs this gate on vibepass_half.) It also explains why B2 (ref oracle) and direct/plain arms look strong.
- What remains true: given a correct alternative, the bug is exposed in 18/20 tasks by an EvalPlus input, and in 9 of
  them the v31 template pool has no such input. The bottleneck is still input reach (v35, v37).

## Paper route status
- Mokav over surviving mutants: no-go (v37). Mokav / CASCADE / TrickCatcher over spec-derived programs: untestable on
  memorized benchmarks (v38). A fair test needs non-memorized tasks (e.g. the self-written diag16 fixtures) and new
  DPP programs, i.e. model calls: not done, needs approval.
- UnitCon, NeuroTestGen, CASCADE, HGFuzzer: author artifacts are Java or C/C++ (audit reviews 036, 015, 056; p0 notes);
  Python PUTs would need a port, which the repo rules forbid without approval → eligibility verdict "not eligible".
  SAVIOR: no verified artifact. Paper route stopped here.

# CHANGELOG v7_vp (copy of v7)

Change vs v7: support class methods (VibePass LeetCode `class Solution`). Inside a class body Python mangles `__d`
to `_Solution__d`, so tracer hooks are renamed `__lf_*__` (dunder names are not mangled) and mutant helpers inside
classes use `__mut_one__` / `__mut_reverse__`. Module-level code behaves exactly as v7.
Files: tracer.py, facts.py, config.json, test_vp.py, vp_check.py.

- Verified 2026-10-13 (CPU): test_vp.py 5/5 OK (module-level traces and facts equal v7 on HumanEval PUTs; class
  methods traced). vp_check.py on the 66 VibePass PUTs, 0 errors (validity evalplus):
  v7 finds inside classes only MUTANT/MUTANT-X/STMT facts (tracer hooks crash with NameError);
  v7_vp finds every kind (BOUND 432, DECISION 682, DU 540, OUTCOME 324, REL 271, ...), top-3 hints now include
  OUTCOME 40, STMT 26, BOUND 11, NUM 11, DU 7 besides MUTANT 57.
  Mutant lists differ only in OIL/RIL loop mutants inside classes (v7 built them with the mangled helper name, so
  they were broken). Output: out/pipelines/v7_vp/heldout_vibepass_real-64611891/vp_check/report_all.json.
- Status: adopted for VibePass held-out (same behaviour as v7 on module-level code).

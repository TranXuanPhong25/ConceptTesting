# v64 CHANGELOG

## 2026-10-25
Copied v55h `experiment.py`; arms defn (v55h answers reused) / brute / plainimpl (v49 instructions); Codex transport code
removed; `seed` copies v55h defn/open/plain answers and checks their prompts are byte-identical; family-effect decision
in `score` (PREREG). prepare + seed + split: 18 new batch calls, 144 per-problem prompts. Registered before any answer.
Amendment 1 (c418e3a): 3 stray writer files moved to misplaced/, one missing closing fence appended; 144/144 valid.
Score done: plainimpl 25/33 prec .96 FA 19; defn = brute 21, 1.00, 0 FA; paired 0–4 → registered "inconclusive";
v49 family effect reverses with Haiku (brute-force abstention). RESULTS.md.

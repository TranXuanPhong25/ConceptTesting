---
name: v56-lcb-fresh
description: 2026-10-25 complete on fresh LCB (11 Qwen-32B PUTs): concept defn vs brute NO-GO (5 vs 6 tasks, 0–1) but FA 5 vs 47; family 4–2 NO-GO
metadata:
  type: project
---

2026-10-24 (Codex): Task B registered in `analysis/v56_lcb_fresh/`; read its
PREREG and CHANGELOG before any mining or scoring. No fresh cohort, no new
PUT and no fresh hidden-test outcome yet. Pipeline cannot freeze until v55
completes. Existing local LCB files are VibePass-filtered, unsuitable for a
fresh cohort. Both private GPU env files were sourced silently; metadata
requests could not connect from sandbox (one explicitly DNS gaierror). This
does not prove endpoint offline. Codex CLI also failed routing discovery.

**Why:** a generalization claim needs new nonoverlapping problems, not more
dev tuning. **How to apply:** pin official source and fixed metadata cohort,
exclude all VibePass problem identities, review adapter and append freezes
before outcomes. Mining cap: newest60 eligible problems ×2 PUT attempts;
no enlargement if yield/result is weak. Codex PUT fallback is authorized but
must be documented; never invent a writer cutoff or post-cutoff guarantee.
Held-out remains unrun. Summary at `analysis/SUMMARY_v48_v55.md` explicitly
marks A/B incomplete. Git commit/push also blocked by read-only `.git`.

2026-10-25 (Claude): user instruction replaced the v55 gate (Amendment 1). Mined
with `mine.py` on Qwen2.5-Coder-32B-AWQ: 120 calls (1 read_error), attempts
public_fail 60 / hidden_pass 36 / hidden_fail 15 / timeout_only 8. Cohort
11/60 problems (easy2 med6 hard3), all wrong-output. Next: user picks the
pipeline-arm writer (Codex quota risk, Qwen-32B, Haiku), then a freeze
amendment before any arm run. Cap reached; do not mine more.

2026-10-25 result (frozen arms.py, Codex certified reference, Qwen writer, 121/121 calls): defn 5 tasks prec .92 FA 5;
brute 6 .51 FA 47; plain 4 .41 FA 36. All three comparisons NO-GO (defn–brute 0–1, brute–plain 4–2, defn–plain 3–2).
Concept gives precision (fewer FA, partly abstention), not tasks. Oracle binds (3677/3720 ~0 valid programs); Qwen
input generator MemoryError on 3/11. 3784 validator uncertified (Codex rc=1). See analysis/v56_lcb_fresh/RESULTS.md.
**How to apply:** fresh-cohort replication of the concept/family effect failed on tasks; do not rerun or enlarge.

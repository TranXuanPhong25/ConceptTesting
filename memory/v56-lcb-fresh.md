---
name: v56-lcb-fresh
description: 2026-10-25 mining done on Qwen-32B: fresh LCB cohort 11/60 buggy PUTs (wrong-output only); pipeline arms not frozen/run
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

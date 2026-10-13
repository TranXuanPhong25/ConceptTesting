---
name: heldout-final-readiness
description: Offline held-out readiness complete; amendment 1 fixes shared 10+4 TC pool; GPU stages remain
metadata:
  type: project
---

(Codex, 2026-10-14) User requested CPU-only preparation while v11_fair GPU work and
v12_rel implementation continue separately. No LLM calls or commit/push authorized
for this task; protected pipeline/run/vendor/PREREG/Kaggle paths remain untouched.

Handoff: `trickcatcher_linefacts/HELDOUT_RUNBOOK.md` and
`pipelines/v11_fair_vp/{CHANGELOG,EQUIVALENCE}.md`; baseline scratch evidence is
`baselines/tests/heldout_dry_amendment1/summary.json`. Use this copy's oracle for final scoring.

**Decision (user, 2026-10-14; PREREG Final protocol amendment 1):** tc_full_v2
keeps the paper's 10 variants + 4 generators/task, shared across K=3 resamples.
Its call cap is per task (14 <= 3*8=24), with <=20 assertions/sample unchanged.
No reduced mode. final_run.py fixes that allocation and attributes its request/
token ledger once across the three rows. The prior 4+4 scratch check is superseded.

**Readiness:** 90 fresh scripted rows across five baselines on 3+3 PUTs pass;
TC costs 42 logical scripted requests/set (14/task), with one shared pool/task.
Tests: class/fairness/scoring 25, analysis 13, common baseline pytest 22,
SymPrompt/ACH 24, TC vote/shared-generation 7. Offline equivalence again matches
133 bundles, 2,793 first request hashes and 16 cached replay rows; two strict
request cache misses are genuine and remain a limit of this CPU check.

**Remaining:** finish/review dev sanity first; VibePass has no genuine mining
cache. VibePass mining, seven-arm generation, all five baseline generations and
shared spec-only references require the GPU. MBPP+ mining can reuse its verified
cache. There is no remaining allocation/configuration decision. Exact commands,
dependencies and logical call bounds are in HELDOUT_RUNBOOK.md (conservative
19,338 VibePass + 3,456 cached-mine MBPP+; 22,794 combined, including refs).

**How to apply:** follow the tracked runbook; do not infer that fake dry-run results
are model effectiveness, or reuse diagnostic evalplus facts as final mined facts.

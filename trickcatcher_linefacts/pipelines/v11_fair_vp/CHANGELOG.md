# CHANGELOG v11_fair_vp

## 2026-10-14 — frozen held-out readiness (CPU only)

Copied from v11_fair, excluding out/ and __pycache__; VERSION is v11_fair_vp.
All four fairness flags, v7 hint ranking, prompts, seeds, K=3, tool versions and
strict generation remain those of v11_fair. Original copies/vendor stay untouched.

- Applied the exact v7 -> v7_vp diffs to tracer.py and facts.py: tracer names
  __lf_*__, class loop-mutant helpers __mut_one__/__mut_reverse__, __force__.
  Module-level mutant source stays byte-identical to the reference.
- Added adapted test_vp.py and vp_check.py. The diagnostic uses this copy's
  workers/output only by default; --versions can request an optional comparison
  whose worker sources are read-only. Its embedded-contract facts are not final
  mined-validity facts and are not seeded into the production facts directory.
- Adapted test_equivalence a/b to compare against v11_fair with all flags on.
  Outputs for both sides remain in this copy. Real local cache replay stops on
  CacheMiss; no response or expected value is invented. CPU timeout override
  affects only the check, not production worker settings.
- Added heldout_support.py: visible-only baseline bundles with empty concept
  metadata, trusted numeric atol and question ids; complete-task ref collection;
  ref-only cached-program reuse and scoring for all baseline rows, including
  empty assertion lists; ref_metrics.json. No judge/B1/post requests.
- Fixed the non-v4 baseline evaluation adapter to score all exported capped
  assertions (rather than the legacy ten-assertion extraction default), and to
  launch its worker with the sanitized environment. The v4 main path is unchanged.
- Added final_analysis.py, copied from analysis/final_protocol.py and routed to
  this copy's oracle/scorer. Includes zero-generation-call witness-only, all
  paper baselines, per-question/task paired tests and 100 seeded random subsets.
- Added tracked HELDOUT_RUNBOOK.md and ignored runlogs README_plan.md.

Verification:
- 23 test_vp + inherited test_fair tests pass.
- HumanEval a: 133 all/hybrid bundles equal v11_fair, flags all on.
- HumanEval b: 2,793 first request keys equal; fresh paired cache replay on
  0/4/16 has equal 16 completed rows and equal two cache misses (new strict
  prompts absent from v7 cache). This does not prove a full online run; see
  EQUIVALENCE.md.
- VibePass mine: first real offline CacheMiss. Final facts/specfacts/bundle
  remain blocked by missing mining, with no substitute validator. Embedded
  contract diagnostic: 66 PUTs, zero errors, every class has non-mutant facts;
  counts match the earlier v7_vp diagnostic (see runbook for all kinds).
- MBPP+ real-12: cached mine/facts/specfacts/bundle all pass offline (2 specfacts
  tasks). No old generation rows or evaluation outcomes were reused.
- Five baseline adapters: 90 scripted rows across 3 PUTs per set x K=3, caps
  pass. Common pytest 22, canonical SymPrompt/ACH unittest 24, tc vote tests 5, held-out scoring adapter regression tests 2. This initial 4+4 TC dry check is superseded below.

Status: implementation and offline checks complete; no LLM endpoint, commit or
push. GPU final run awaits dev sanity completion/review and genuine VibePass mining.

## 2026-10-14 — Final protocol amendment 1 readiness

- TC allocation is resolved in PREREG: fixed 10 variants + 4 generators/task,
  shared by K=3 resamples, within the 24-call/task budget; <=20 assertions/sample.
  No reduced mode. Prompts, hint ranking, four fairness flags and main seven-arm
  generation stay frozen. Original v11_fair, v12_rel and vendor remain read-only.
- Updated HELDOUT_RUNBOOK.md with exact fixed-pool commands and cost estimates:
  conservative <=19,338 VibePass / <=3,456 cached-mine MBPP+ logical requests.
  Its final analysis executes with the same dedicated interpreter as scoring.
- Synced final_analysis.py with the verified general analysis implementation:
  manifest K validation, input-directory write protection, fixed replay hash seed,
  main-thread mutant preparation and stable ref/full report ordering. Added
  test_final_analysis.py (13 CPU tests); no model requests or reconstructed arms.
- Reverified class-method/fairness/scoring tests (25), baseline common pytest
  (22), canonical SymPrompt/ACH tests (24), TC vote/shared-generation tests (7).
  Repeated a/b equivalence and the five-baseline 3+3 PUT dry run; results are in
  EQUIVALENCE.md and baselines/tests/heldout_dry_amendment1/summary.json.
- Status: CPU readiness complete; genuine VibePass mining and all held-out
  generations/shared refs need the GPU after dev sanity is reviewed. No commits
  or pushes, no secrets or online calls.

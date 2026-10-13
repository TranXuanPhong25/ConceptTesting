# v11_fair_vp vs v11_fair — CPU evidence, 2026-10-14

All four frozen fairness flags are true and equal. Main generation keeps the
reference recipe; VERSION and the documented class-method fix differ. Additional
held-out scoring/analysis helpers and the non-v4 baseline adapter are documented
in CHANGELOG.md. The reference sources were read without writing there.

- Adapted check a: all-task and hybrid HumanEval bundles equal on all 133 PUTs.
- Adapted check b: all 133 x 7 arms x K=3 = 2,793 first request hashes equal,
  using real classifier observations created by these checks (not historical
  expected outcomes). Earlier observations in the check's own output can resume.
- Fresh paired cache replay, tasks 0/4/16, K=1, flags on: equal completed row
  semantics, request hits/misses and CacheMiss boundary in both copies; 16 of
  21 rows completed, 24 cache hits, two request misses. New strict expected-value
  prompts are absent from the historical v7 cache. No response was fabricated.
- Comparison excludes only elapsed timing and source-derived run_id. The CPU
  classifier test timeout was 30 seconds on the resumed run, after the first
  attempt stalled at task 63; production timeout is unchanged. All 133 result
  files exist. The original test process was stopped before restarting.
- Adapted test_vp verifies AST/site identity, module-level mutant source identity
  over every selected HumanEval PUT, equal synthetic module traces, and class
  tracing/loop mutation/forced conditions. Combined with test_fair: 23 tests pass.

The replay is intentionally incomplete at genuine cache misses. This establishes
CPU compatibility and the matching replay boundary, not equivalence of a complete
online held-out run. Exact execution evidence lives in ignored
out/humaneval/equivalence/equivalence.json.

Amendment 1 re-verification: a/b ran again offline after the shared TC adapter
and analysis updates. All 133 bundles and 2,793 first-request hashes still match;
the paired replay again matches 16 completed rows, 24 cache hits and the same two
genuine cache misses. The TC adapter uses exactly 10 variants + 4 generators per
task, outside main-pipeline generation. No protected source/output was written.

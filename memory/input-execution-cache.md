---
name: input-execution-cache
description: User requests shared per-input cache; modern pipeline caches isolated reference/PUT outcomes with separate repeats and full execution identity
metadata:
  type: project
---

User2026-11-05 asks to cache already executed inputs to avoid repeated execution,
then run plain+BVA using a newly supplied Qwen27endpoint;fix errors autonomously.
Endpoint stored only in private runtime config outside repo.

Implemented `final/modular/execution_cache.py`,SQLite shared across modern runs,
reference/domain+PUT results after generation freeze only. Generator never reads
execution outcomes. Keys include code/context/contract/expected/seed/timeout/atol,
typed bound inputs,dict insertion order,float bits,runtime/harness/executor and
separate repeat0/1. Each cache miss uses a fresh bwrap sandbox; do not auto-import
old batched outcomes as equivalent observations. Timeouts/infrastructure failures
not reused;corrupt entries recompute;per-keylocks prevent duplicate computation.

CLI --execution-cache defaults final/out/execution_cache;--no-execution-cache
restores batch execution. Run checkpoints remain authoritative/read-only. Summary
receipts expose hits/misses/executions;cached duration is historical.112modular
checks pass.8inputfixture cold.5399s/warm.0115s with0warmexecutions;not end-to-end
benchmark speedup. Follow PREREG cache amendment before interpreting live results.

Live6PUTsmoke completed:432native-input/repeatrecords,428executions/4hits cold.
Postrun audit forbids subprocess creation,reconstructs all24jobs and gets432hits/
0new executions/0modelcalls in.1202s,exact artifact equality. Fullread-only replay
also matches summary. No claim that this warm execution time includes generation.

**Why:** inputs repeat across methods and development runs while reference/PUT
source often stays fixed. Reuse should save execution time without leaking outputs
to generators or silently removing a required confirmation observation.

**How to apply:** retain complete cache identity and isolated-input semantics;
change generation methods using a fresh run directory but the same shared cache.

2026-11-07 user explicitly approves conditional PUT confirmation: stop after a
first pass; repeat only first fail/error/timeout and count detection only when the
confirmation also fails/errors/timesout. This supersedes always repeating every
PUT/input. Reference/domain acceptance remains two observations. See the dated
PREREG amendment and final/src/modular/stages/put_evaluation.py; unstable now covers
only retested inputs, whose original indices are recorded. New retry checkpoints
and stage policy distinguish this from historical full-suite repeat artifacts.

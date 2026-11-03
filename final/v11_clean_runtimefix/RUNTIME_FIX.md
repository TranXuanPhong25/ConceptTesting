# Coverage collector deadlock — 2026-11-01 continuation

User noticed no progress. The old155case count had not advanced for13minutes;
both native workers (case151 and156) used0CPU over repeated samples and waited on
futex, despite live parent/supervisor heartbeat. py-spy independently captured the
same stack in both workers:

`coverage.collector._clear_data -> flush_data -> get_data -> V11Coverage.measure`.

Both process trees were single-threaded; wall time was13/28minutes while actual
CPUtime was1.9/2.7seconds. Cases use generator-based string_sequence with broad
integer strategies. The stack/zero-CPU evidence distinguishes this from slow
mutation analysis. Original service was stopped; snapshots preserve all completed
results/responses (4439artifacts) and the blocked worker stacks.

## Runtime-only correction

- New folder/output continuation; original V11 source and old run are unchanged.
- Same pinned coverage7.16.2, supported `COVERAGE_CORE=pytrace` worker option instead
  of its default C tracer. No private lock manipulation or vendor code patch.
- Coverage timeouts can interrupt generator tracing. Python tracer uses try/finally
  around its data lock, avoiding the observed C tracer collector lock path.
- Normal branch/loop/generator fixture lines/arcs must match between cores.
  Repeated generator timeouts must still allow later measurements to complete.
  Timing-sensitive/timeout boundary coverage may differ because tracer overhead
  differs; do not claim bitwise identical fuzz facts for every timed-out input.
- Monitor worker process-tree CPU progress. After120seconds with no CPU progress,
  terminate the sandbox and retry the SAME job once in a fresh process, without
  model calls or changing sampling seeds. Two idle failures raise WorkerStalled
  as infrastructure failure, never silently convert to empty concept evidence.
- Every native attempt has a fresh writable scratch directory, including retries
  after controller restart. One overall wall deadline covers both attempts; an
  inactivity restart does not reset/extend the original registered timeout.
- Record per-worker CPU ticks, idle seconds and elapsed time in worker_progress;
  heartbeat includes this evidence instead of relying only on process liveness.
- Keep original per-call alarms, wall time limits, tool versions, prompts, fact
  ranking, model parameters, cohort, oracle and sample/control logic unchanged.
- Old completed cases/native results/cached model responses are imported byte for
  byte. Only unfinished workers151/156 and later cases use the fixed runtime.

Before restart: run engineering parity/timeout/watchdog tests and independent
read-only review. No LLM completion or native cohort outcome replay before clearance.
Continuation manifest records coverage core, idle policy and imported provenance.
No outcome-based selection, extra model retries, new PUT generation or benchmark
enlargement. Register this transport/runtime correction separately from efficacy.

If the one overall deadline expires after an idle restart, treat that as the same
infrastructure failure rather than a bad strategy, empty fact pool, or zero-evidence
method result. This also applies if archival/setup consumes the remaining deadline.

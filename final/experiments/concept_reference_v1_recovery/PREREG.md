# Transport-only continuation — 2026-10-31

User requests fixing the stopped run and continuing, then explicitly requests a
retry after20minutes. Scheduled earliest retry:2026-10-31T06:38:15UTC. No endpoint
inference before that deadline. Current endpoint returns404 for models/tokenizer.

This is a transport-only continuation of concept_reference_v1, not a new semantic
treatment. Same fixed164-task cohort,20-input budget, five model arms, witnesses,
prompts, seeds, sampling parameters, context budget, analyzer and reference oracle.
The frozen cohort is required; writer calls are disabled. The original run/source
remain intact. Imported18input task files and91responses are copied byte-for-byte
and validated through an import manifest (331files total, including observer logs).

Changes:

- Receive SSE tokens incrementally instead of waiting for a complete buffered HTTP
  response. Wire changes are stream=true and stream_options.include_usage only;
  messages/model/temperature/seed/max_tokens/thinking settings are unchanged.
- Idle socket timeout180s; overall active-generation deadline1800s. Preserve partial
  text on interrupted streams, but never score or parse incomplete output as a test
  suite. A completed finish event can be retained if only its usage footer is lost;
  mark usage completeness explicitly.
- Safe tokenizer operations retry at most3 times with5/20s delays; they do not count
  as completion attempts. Completion failures retry at most3 attempts per logical
  call INCLUDING archived legacy unknown attempts, with identical parameters.
  For task16/classical one legacy attempt leaves at most2 new attempts. Retry
  counts persist across controller restarts.
  Nonretryable errors and exhausted caps stop. No model fallback or JSON repair.
- Preserve all failed completion attempts as sibling call directories, including
  the original task16/classical unknown request. Existing call accounting therefore
  retains historical unknown usage and every extra HTTP completion attempt.
- Scheduler waits for the user deadline AND reviewed/tested source hashes. It polls
  metadata only while endpoint is unavailable, checking expected model/context.
  It resumes from durable checkpoints. Read-only transport failures may cause a
  supervised restart; exhausted completion attempts do not reset.
- Read endpoint configuration only from the private env file outside the repo;
  allow a replacement endpoint with the same expected model. Never persist URLs,
  keys or raw exception messages. Store structured operation/status/error type.

No scored benchmark outcomes have been read or computed. No cohort, saved prompts,
received responses, accepted input artifacts, or reference expectations are altered.
Independent read-only review and regression checks precede release of the scheduler.

## Final review and release, before any recovery completion

- Independent Codex review cleared the continuation; combined engineering suite
  passes42/42. Regression cases cover IncompleteRead both before/after finish,
  completed output with a lost usage footer/deadline, safe tokenizer read retries,
  permanent failures, persistent retry caps, legacy accounting and model pinning.
- Model is explicitly pinned to qwen3.5-27b-awq; startup env changes cannot select
  another model. All92 imported request records reconstruct with exactly the same
  messages/temperature/seed/output cap; all331 imported artifacts match hashes.
- Review fixes wrap metadata/tokenizer HTTP read exceptions; preserve completed
  output on footer errors; count legacy attempts in the total3cap; separately
  report unsent keepalives and responses with missing usage footers.
- Replaced the pre-review scheduler process with PID115270, loading final code.
  Ready guard locks27 source/data hashes and is verified before launch/restart.
  Scheduled time remains06:38:15UTC (13:38:15Vietnam), with no completion before it.
- If metadata remains unavailable, scheduler only polls models every60s. Read-only
  transient failures can restart the controller; completion caps remain persistent.

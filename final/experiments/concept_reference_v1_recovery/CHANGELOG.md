# CHANGELOG

## 2026-10-31 — resilient transport continuation

- New isolated folder; original v1 source and output preserved.
- Reuse unchanged v1 analysis/prompts/oracle/worker and frozen PUT cohort.
- Copy benchmark/controller orchestration with dependency imports redirected to
  streaming transport and persistent retry checkpoints; no treatment changes.
- Import331existing artifact files:18input tasks,91received responses.
- Add scheduled retry after20minutes, metadata liveness gate, review hash gate,
  finite retry budgets, partial-stream handling and structured safe errors.
- New code uses descriptive names and explicit control flow per user preference.
- Validation:42/42combined engineering checks pass, independent review cleared.
  All92saved request records reconstruct exactly;331imported artifact hashes match.
- Final schedulerPID115270 waiting for13:38:15Vietnam;27reviewed source/data hashes
  locked. Metadata only while offline; no recovery completion before user deadline.
- Read-only404/read failures are supervised; legacy-inclusive total3completion
  attempt cap survives restarts. Completed output survives usage-footer failures.

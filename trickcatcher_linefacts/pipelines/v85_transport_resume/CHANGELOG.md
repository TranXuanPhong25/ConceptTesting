# V85 restored endpoint — 2026-10-28

- Copy the v85_contextfit continuation runner; use the same generation, oracle
  and transport implementation without changing concept retrieval/binding.
- Import113prepared tasks,25paired checkpoints and574successful request receipts.
- Preserve one timed-out request as unknown usage; count it toward the original
  cumulative cap and explicitly record the user-authorized fresh attempt.
- Regression checks cover budget exhaustion, retained unknown usage and prevention
  of double-counting the historical timeout in final accounting.

7focused CPU checks pass;574request identities and3900parent output files
verified/frozen. PID54121 launched2026-10-28 15:04:58UTC;25pairs restored and
new completion received. No final efficacy result yet.

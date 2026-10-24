# Independent Codex review, before outcomes

2026-10-24. Reviewer: `/root/v55_review`, separate read-only Codex agent;
user's explicit Codex reviewer choice overrides the old Sonnet-only memory.
Reviewer inspected the PREREG, runner and engineering tests, without writer
generation, model-program execution, hidden-test execution or outcome scoring.

Initial review: request changes. Applied findings:

1. Reserve attempt directory before the subprocess. Timeout, launch error or
   interruption leaves unresolved state and cannot trigger an automatic retry.
2. Audit attempted tool items at started/updated/completed events, not only
   completed. Any tool activity rejects the call.
3. Preserve sanitized primary quota observations from isolated CODEX_HOME
   before deletion. Select the newest observation across isolated and host
   sessions; require fresh host evidence when writer quota is missing.
4. Report explicit abstention counters in addition to finishing reach.
5. Define and enforce syntax/entrypoint malformed answers and generator
   execution failure as incomplete; no repairs. PREREG Amendment2 precedes
   all writer outputs/outcomes. Normal zero-yield remains reported failure.
6. Pin reviewed manifest actually used by execution. Final reviewer requested
   using HERE/MANIFEST.json directly or checking copy equality. Both generate
   and score now read HERE/MANIFEST.json; lifecycle check verifies prepared
   copy equality and every prompt hash.

Additional source/PREREG/manifest/dependency hash gate blocks drift before
generation/scoring. Repository-hidden PID-namespace probe exited 0. Five
lifecycle tests pass: unresolved timeout/no repeat, newest isolated quota,
paired manifest/separate k calls, reviewed-source drift, syntax/entrypoint.
These are engineering checks, not efficacy evidence.

Final reviewer conclusion: no further code blockers after manifest fix;
transport remains an operational blocker. Full CLI generation remains untested
in this restricted environment. No positive or negative scientific verdict.

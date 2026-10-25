# Scoring status: provisional, not a scientific verdict

2026-10-24. The initial implementation executed P0B prematurely before its independent code review, violating the intended review-before-outcome sequence. Preserve this deviation explicitly.

`out/`, `out_repaired/`, `out_repaired2/`, `out_repaired3/` are instrumentation-failed attempts: missing dependency/configuration and relative worker job paths. `out_repaired4/` contains provisional labels from an unreviewed comparator/worker implementation. These outputs must not be promoted to research results or used for feature/cohort selection. Their source/instrumentation limitations remain recorded; none is overwritten.

Reviewer subsequently found contract-error classification, AssertionError handling, comparator-policy, cache identity, exception oracle and serialization defects. Repairs are in progress in the scorer/worker. No fresh private scoring has occurred after those findings. P1 source-only routes and finite repair budgets were frozen before any of these private outcomes; do not change them based on provisional wins.

Missing before P0 closure: independently approved evaluator instrumentation, full verified manifests/cache integrity, dedup/expectation-conflict reporting, problem/task metrics and witness/cost audit. Some reporting has been implemented but is not approved yet.

Later update: reviewer gave scoped PASS for fresh retrospective scoring after explicit bool validity, phase-aware exception/serialization handling, original comparator, cache hashes/integrity, atomic/locked publication and complete reporting were repaired. Authored worker regression tests pass. Fresh `out_reviewed/` completed; RESULTS.md reports separately from prior provisional attempts. Result release flag remains conservative; no claim of independent semantic re-adjudication of every reference. P2/P4 integration continues separately in v61.

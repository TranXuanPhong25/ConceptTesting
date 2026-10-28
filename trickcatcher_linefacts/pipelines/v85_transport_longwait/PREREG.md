# V85 completion timeout repair — 2026-10-28

User asks to check the standing full113 run. The previous controller stopped
16:10:45UTC on task124 baseline strategy correction after240.81seconds. A nearby
successful4096-token response took237.20seconds, leaving only3seconds under the
old timeout. At16:22:37UTC the exact model/context is reachable. The failed
request's server outcome is unknown; these observations do not prove its cause.

Before any new completion, register one transport-only change for both arms:
completion HTTP read/connect timeout900seconds; tokenizer240seconds/models25
remain unchanged. Keep prompt bodies, output budgets, seeds, context allocation,
concurrency2,2rounds,10shared refs/task and card-to-fact binding unchanged.
No automatic transport retry loop. Longer waiting also delays detection of a
genuinely stuck completion; it does not guarantee server availability.

Resume in comparison_contextfit_4 under the standing execution request. Import
113prepared tasks,54complete pairs (55v11/55retrieval final rows on different
task sets) and694successful receipts. Preserve3failed physical attempts with
unknown usage, including the latest baseline task124 request:
4d80ea92d52a1680a194d437792786e866c22c1de1993239716c8f3f94bbb6c8.
This recovery makes one new attempt at that unresolved request. Active ledger
starts694, historical unknown3;697cumulative attempts already spent. Set active
cap3500 so cumulative cap remains3503, leaving2806new attempts.

Freeze source/protocol and all parent outputs; verify imported request identities
before launch. Preserve previous roots unchanged. Target canonical/contracts stay
grading-only after generation and shared oracle freeze. All113remain denominator.
No efficacy conclusion until completion. This does not remove the existing
dependence on fuzz-generated facts for binding retrieved concept cards.

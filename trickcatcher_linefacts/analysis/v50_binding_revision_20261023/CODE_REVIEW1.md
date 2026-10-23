# Independent clean-context implementation audit — REQUEST CHANGES

2026-10-23 reviewer v50_code_audit, read-only. 28 synthetic tests passed.
No preparation, Qwen, real diagnostic PUTs or endpoint calls.

Must-fixes:
1. Guard each HTTP, including completion after tokenizer, against quota/window drift.
2. Models metadata needs durable attempts/cache and unknown-attempt consumption.
3. concept=unknown with a known relation must not be labelled vocabulary-incompatible.
4. Freeze evaluator-only facet/control rules before outcomes; clarify unknown labels,
   multifacet relations, E8 empty/unknown handling and semantic vs interface failures.
5. Freeze terminal failures and quota checkpoints, not only complete generation.
   Keep per-request quota checks, not only the latest snapshot.

Parent fixes in new v50 copy only: request callback before reservations, metadata
raw-response/attempt ledgers and preflight IDs, consistent unknown checks, EVALUATION.md
hash in approval/freeze, immutable stop checkpoints and append-only quota snapshots.
Added focused regressions and requested re-review before prepare. Old v43 remains
unchanged. This document preserves the initial REQUEST CHANGES disposition; it is
not an approval of later code.

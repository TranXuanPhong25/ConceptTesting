# Retrieval v3

2026-10-26: user requests evaluation of concept quality and further retrieval
improvement, supplying Qwen3.5-27B-AWQ endpoint. Read-only model metadata and a
transport-only JSON probe succeeded (no thinking tokens). New protocol and folder
created; v2 artifacts preserved. Task inference not yet launched.

2026-10-27: original retrieval113/113 cached; continuation in
`continuation_20261027/` preserves frozen scripts and raw responses. One oversized
judge receives an explicit compact witness presentation; utility drains original
queue and exact-cache restoration handles identical arm requests without retry.
Added completion-aware report, manual20-row native review and purposive claim
audit. Separate opt-in v4 implements generic duplicate recovery/interleaving;
no extra model calls for v4 scores, no default engine promotion.

2026-10-27 COMPLETE:120arm slots/112unique utility requests,351native rows;
plain4/v2 18/v3 15confirmed bug tasks outof40, false-alarm tasks0/2/4.
7missing records restored from exact terminal caches,8slots share identical
request responses overall.0unknown usage.60tests PASS; frozen sources/code PASS.
See RESULTS.md and continuation FINALIZED/FINAL_VALIDATION. V2 stays default.

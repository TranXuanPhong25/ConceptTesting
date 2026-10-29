# VR9 complete: routing/retention repair works mechanically, no efficacy gain

2026-10-29. User restored the registered Qwen3.5-27B-AWQ endpoint and authorized
continuation. Frozen source/parent/inputs stayed unchanged. Linux pinned runtime
used5new single-attempt expected-output completions; all received,0unknown usage.
Strategies and strict/generic outputs replay exact historical receipts. No fresh
strategy/reference generation, fallback, full113 expansion or duplicate controller.

| Metric | Strict | Retain | Applicable + retain | Generic |
| --- | ---: | ---: | ---: | ---: |
| Primary shared-ref confirmed tasks /6 | 6 | 6 | 6 | 6 |
| Primary false-alarm tasks | 0 | 0 | 0 | 0 |
| Secondary own-oracle confirmed tasks /6 | 5 | 5 | 5 | 5 |
| Secondary false-alarm tasks | 2 | 2 | 3 | 3 |
| New valid inputs selected after round1 | 19 | 24 | 24 | 23 |
| New selected inputs satisfying the OBS predicate | 7 | 6 | 6 | 7 |
| Selected bug-exposing calls, final native labels | 2 | 1 | 1 | 2 |
| Task51 new selected valid inputs | 0 | 4 | 4 | 4 |
| Task51 selected bug-exposing calls | 0 | 0 | 0 | 0 |

Bug-task detection was already6/6at round1; no added task or equivalence claim
follows from the final tie. Input/call counts are not independent task successes.
More retained inputs alone is not better semantic coverage or oracle accuracy.

The repaired routing skips the statically refuted vowel-class mismatch at task51
and uses generic exploration. The retain arm keeps the same semantic pool but
admits valid non-hits. Both recover4selected valid inputs at that task, yet none
of those selected calls exposes its actual space-deletion bug. The previously
discarded exposing witness is not automatically recovered by bounded seeded
selection. At task101 selection changes reduce exposing calls2→1; task detection
is unaffected because round1already catches the bug. Report this loss alongside
the retention recovery.

Secondary false alarms remain at tasks98/101for strict/retain, with task51also
flagged in applicable/generic. The refuted local membership hypothesis is not a
proof of function correctness or a repair of the expected-output model. Only
that one task changes applicability routing; this replay does not evaluate a new
strategy writer or broad general applicability reasoning.

## Cost and integrity

5fresh completions out of cap12,2,918prompt+824completion=3,742new tokens.
0failed/unresolved attempts and0unknown usage. Reused round2 pool:20physical
receipts/18,108historical tokens. Reused6round1+60refs:30,099historical tokens.
Relevant known subtotal51,949tokens counts each of those receipts once; shared
preparation costs are excluded.71logical round2 calls including replays are not
71new API calls. No new paid provider fallback was used.

Generation freeze precedes final native grading. Original80source/input and63
parent hashes are unchanged; final raw outputs, receipts and exact replay checks
are covered by FINAL_AUDIT.json/md. COMPLETE marker and controller exit observed.
No benchmark continuation or automatic next experiment follows.

## Decision

The engineering repair prevents treating this refuted hypothesis as a mandatory
target and retains valid non-hits. The current package does not show improved
bug exposure or oracle quality. Preserve these results and do not promote or
enlarge this experiment to claim a concept gain.

The separate vr10 retrieval diagnostic also fails its incremental-dense gate;
therefore no V7 embedding→VR9 integration is started here.

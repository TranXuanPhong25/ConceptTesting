# VR12 expanded VR9: complete, no demonstrated applicability gain

2026-10-30. User requested more VR9 samples; the registered census includes all
11fresh eligible tasks, four arms,K1. Only2targets are OBS-uncovered;9are already
covered controls. The separate vr13 retriever is not integrated into this run.

Local timer launched00:45Vietnam and controller finished00:57:54.39physical
completions,39,878newtokens,0unknownusage. Saved11R1+110reference responses reuse
50,918historicaltokens, counted separately.118logicalround2calls share exact-body
cached responses. No retry or paid fallback. Current controller absent, lockfree.

## Results on 11 tasks

| Metric | strict | retain | applicable | generic |
| --- | ---: | ---: | ---: | ---: |
| Saved round1 ref-confirmed tasks | 7 | 7 | 7 | 7 |
| Final ref-confirmed tasks | 9 | 9 | 9 | 8 |
| Ref false-alarm tasks | 1 | 1 | 1 | 1 |
| Saved round1 o0-confirmed tasks | 5 | 5 | 5 | 5 |
| Final o0-confirmed tasks | 6 | 7 | 7 | 5 |
| o0 false-alarm tasks | 10 | 9 | 9 | 10 |
| Selected exposing input occurrences, summed per task | 10 | 7 | 7 | 7 |

Ref replaces own expected values using the saved spec-only reference pool;
o0 uses generated expected values. A task can have both a correct bug-revealing
assertion and false alarms, so their task counts need not sum to11.

All semantic arms add tasks27/118 over R1; generic adds27only. Applicable does
not beat retain or strict on the primary ref result. Its paired contrast with
generic is1win/0loss, exact sign-test p=1.0, not convincing evidence of an effect.
Do not pool the old six VR9 tasks as fresh replications or claim held-out utility.

Strict/retain draw receipts match on all11tasks (20drawpairs;89has no draws).
Retention still reduces selected exposing occurrences10→7. Exposing selections
without a correct expected failing assertion are4/2/2/4 respectively; cases
without any matching assertion are0/1/1/0. Input retention, semantic OBS hits
and final oracle success are different measures. No default promotion, larger
automatic run or integration of vr13 is supported by this census.

## Verification and interpretation

79source/input+64parenthashes, independent approval,1,542generationhashes and all
39request/response identities verify. All16arm/oracle summaries reproduce exactly
under the pinned Python3.11.14, without executing PUTs/references again.

The scheduled audit initially reported FA/abstention differences. Root-cause
analysis reproduced those differences only with unpinned Python runtimes:
Unicode-dependent `ast.unparse` spelling misses a saved call key for task27.
No frozen result repair is needed. Read RUNTIME_AUDIT_ADDENDUM.md and
RUNTIME_AUDIT.json; earlier audit reports are preserved as historical evidence.

The bottleneck remains semantic binding and input/expected-output delivery,
not a demonstrated benefit from more samples or embedding alone. Vr13's separate
28-source development regression prunes proposals but still has one known-site
loss. That evidence is not a license to silently alter this completed experiment.

The raw local run is archived in
`pipelines/vr12_expanded/completed_vr12_20261030/artifacts.tar.gz` with a hash
receipt alongside it. No new inference was needed for this continuation.

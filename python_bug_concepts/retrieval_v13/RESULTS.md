# vr13: cleaner proposals, incomplete site recall

2026-10-29. User-authorized V7 improvement, evaluated only as development
regression on the same exposed 28 sources: 12 buggy, 12 canonical and four old
engineering fixtures. No new held-out result or downstream generation claim.

The actual V7-derived runtime adds operation-specific binding, explicit unknown
abstention and no forced top-three fill in vr11. Vr13 corrects two role omissions:
repeated-literal `.replace` versus maximal runs, and lexical direct recursion.
Corpus, evidence overlay, candidate budget, channels and pinned Jina code encoder
remain unchanged. Only binder variant G was evaluated; Q/F were not run.

## Results

Current-base arm A, top-three cap, 12 buggy sources; all current bindings graded.
Counts below use the same final union of exact-source judgments for both columns.

| Metric | Frozen V7 | vr13 G |
| --- | ---: | ---: |
| Returned bindings | 36 | 26 |
| Queries with any proposal | 12 | 12 |
| Old annotated first-site hits | 8/8 | 7/8 |
| Agent-reviewed supported fault bindings | 9 | 9 |
| Agent-reviewed contradicted bindings | 22 | 14 |
| Unknown/conditional | 1 | 3 |
| Still ungraded | 4 | 0 |

On the 12 canonical sources, proposals fall from 36 to 18, all 18 judged
contradicted; nine sources still receive proposals, three abstain. This is not
an emitted false-alarm rate: retrieval hypotheses are not final bug reports.
Operation presence remains insufficient to establish semantic applicability.

Across A-D the buggy known-site count is 7/8; returned counts are 26/28/25/28.
All 28 source queries have exactly identical candidate objects to frozen V7 in
each arm. This isolates binding changes; it does not demonstrate a dense recall
gain. The earlier vr10 dense diagnostic remains NO_GO.

Vr11 had 6/8 annotated-site hits. Vr13 restores task140's correct fixed-chunk
replacement site, but task109 remains a site-localization miss. Keep that loss
visible alongside the reduced proposal volume; see LOSS_109_AUDIT.md. Neither
runtime is promoted to the public default or silently inserted into VR12.

## Review and provenance

Implementation and evaluation were independently approved and frozen before
retrieval. The worker received source strings only; predictions were sealed
before scoring. All 26 authored engineering checks pass. See the engineering
and semantic final audits for independent integrity verification.

Scoring reuses 117 old development judgments, plus 24 exact-source/binding-matched
vr11 judgments and one newly method-blinded source-only agent judgment. That one
judgment supports task140's `.replace("___", "-")` maximal-run mismatch. The
same binding already existed in V7, so V7's supported count is now 9, versus 8
in the earlier vr11 report. This is an annotation-completeness change, not a
new supported binding gained over V7. No reviewed supported binding is lost.

The 25 current previously-ungraded unique bindings comprise 2 supported,
21 contradicted and 2 unknown. Prior judgments were reused only after exact
source, concept, line/end-line/expression equality; all quoted source checked.
These are agent judgments on exposed development sources, not human gold or
formal proof. No generalization or test-detection efficacy is established.

Reproducible receipts: evaluation_development/run01/RESULTS.json,
RETRIEVAL_SEAL.json, GRADE_JOIN_FREEZE.json and REVIEW_SUMMARY.json.
Immutable pre-run README/CHANGELOG/freeze statuses describe their historical
checkpoint; this report is the later outcome, without rewriting frozen files.

## Expanded VR9 is separate

The requested larger VR9 run is registered as
`trickcatcher_linefacts/pipelines/vr12_expanded`: all 11 remaining eligible tasks,
four arms, K=1, at most 132 physical completions. Only two fresh targets are
OBS-uncovered; nine are already-covered controls. CPU/review readiness is complete,
but endpoint preflight failed and a separate metadata probe returned HTTP404.
Zero completions/tokens and no final scores; no active controller or paid fallback.
Resume requires a live authorized endpoint and frozen preflight, not a new method.

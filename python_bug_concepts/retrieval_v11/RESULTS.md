# vr11 binder development regression

2026-10-29. Actual V7 copy with operation-specific source screening and abstention.
Frozen before inference after independent review;15authored engineering tests pass.
Same old28source queries and exact V7A-D candidate objects, unchanged model/corpus.
This reuses exposed sources/117judgments that informed implementation; it is
development regression, not held-out retrieval efficacy or test generation.

| Current-base armA on12buggy sources | Frozen V7 | vr11G |
| --- | ---: | ---: |
| Returned bindings | 36 | 25 |
| Queries with any returned binding | 12 | 12 |
| Old known first-site hits | 8 | 6 |
| Reviewed supported bindings | 8 | 8 |
| Reviewed contradicted bindings | 22 | 14 |
| Unknown/conditional bindings | 1 | 3 |
| Ungraded old bindings | 5 | 0 |

Canonical12queries: returned36→18;9queriesstillhaveproposals,3abstain. Reviewed
contradicted proposals34→18 (two old ungraded). These are proposal judgments,
not emitted bug reports or a calibrated precision estimate. Pruning still leaves
incorrect proposals; observed operation presence does not establish applicability.

All24new/previously-ungraded bindings were method-blind source-reviewed, frozen
before unblinding:1supported (third-repeat membership toggle),21contradicted,
2unknown. Exact-source old-grade reuse is disclosed. A-D full tables, losses and
grade hashes are preserved in evaluation_development/run01/RESULTS.json and
REVIEW_SUMMARY.json. No Q/F or post-outcome ranker/model tuning was performed.

Two labelled first-site losses expose operation-role completeness defects:
fixed-chunk-run incorrectly accepts slicing although its card specifies literal
replacement; recursive-base-progress lacks a corresponding recursive-call role.
These losses are not hidden by lower returned counts. Any repair belongs to a
new version; this source/freeze/outcome remains unchanged. No default promotion
or integration into the expanded VR9 experiment is made from this result.

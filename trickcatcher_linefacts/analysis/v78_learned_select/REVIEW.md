# Independent review record

Reviewer: independent read-only Codex agent `/root/v78_readonly_review`, invoked under the recorded user review requirement. The reviewer did not generate labels or fit models before approval.

## Before outcomes

1. Initial review: STOP for missing historical pool identity check. Required `sha256(json.dumps(inputs)) == v41.inputs_sha256`; also recommended refusing repeated reads with changed hashes. Both fixed, amendment recorded, synthetic tests10/10; reviewer GO.
2. First invocation stopped at the prospective duplicate-spec guard before label reconstruction/fitting. Original approval and stop record preserved. Public-source grouping identified24 exact specifications in33 PUTs.
3. Grouped protocol review: GO after verifying whole-spec-group holdout, equal group→PUT→item training weights, priors aggregated at group level, and whole-group bootstrap.11/11 synthetic tests pass. The final source/protocol fingerprints are in `APPROVAL.json`.

## After the frozen run

Audit **PASS**. Reviewer independently recomputed from saved scores/labels, without fitting models:

- Source manifest matches final approval; all1,743 consumed input fingerprints remain unchanged.
- Both arms contain33 PUTs/24 groups. Every fold excludes all specification siblings and trains on23 other groups.
- Exact tie expectations, uniform/per-kind baselines, distinct-input costs, cost-conditioned controls, aggregate scores, group bootstrap, and prospective gates agree.
- Primary context18 < random18.248965 and subtype prior20.5; all three gates fail. Secondary21 equals context-removed/subtype21 and cannot replace primary.
- Scoped NO-GO is supported; no population-level harm or universal impossibility claim. Metric is input exposure, not assertion correctness.

Reviewed `RESULTS.json` SHA-256: `07d78c9cee453f2982c3d3f7e7ec95c85fb699f2edcc8ea3fa229dbea7ab7220`.

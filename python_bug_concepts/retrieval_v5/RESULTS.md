# V5 scoped facts: engineering complete, no retrieval gain

2026-10-27. Old baseline committed/pushed first as163b58a. V5 is an actual copy of
v2, with the parent/file hashes in COPY_MANIFEST.json. No old source or frozen
labels changed. New implementation/config was frozen before scoring.

| Same113PUTs, unchanged labels | V2 | V5 |
| --- | ---: | ---: |
| Bug-family hit@3 | 88 | 88 |
| Family + first selected source-site hit@3 | 74 | 74 |
| Family + any of up to3sites hit@3 | 83 | 83 |
| Returned cards | 275 | 275 |
| Frozen-label match rate among returned cards | 34.9% | 34.9% |

No task-level site wins or losses. No scoped-backend fallback on113sources.
The development/audit designations are historical; both were previously inspected.
Labels are incomplete, single-author and development-informed. Label-match rate
is not an actual-bug precision estimate. No v5 native utility result exists.

## What the implementation adds

- LibCST exact source/scope/qualified-name metadata; all275returned bindings cite
  an actual node/span, independently checked against original source text.
- Bounded local value-origin chains, with64returned leading sites marked as an
  observed local output dependency;211remain unknown, not assumed irrelevant.
- Conditional requires/excludes and a transparent exclusion ledger. Four raw
  index bindings across three tasks were excluded by guard/loop checks; none
  changed the final top-3 outcome. They are not counted as four confirmed bugs
  fixed or four independently certified false positives.
- Model-free where/how/what grounding: expected output remains unassigned instead
  of inventing an oracle or a distinguishing example.

These are engineering/interface changes. The observed result does not establish
better actual-bug precision, recall, source localization or test-generation utility.
Broad candidate priorities remain dominant; the newly added exclusion conditions
mostly act below top3 on this cohort. No post-score rule tuning was applied.

## Verification and disposition

118tests pass, including32new scoped tests: branch polarity, scope isolation,
shadowed builtins, UTF8/Unicode column mapping, rebinding before/after guards,
alias/unknown mutation, slice/deletion mutation, loop index reassignment,
first-tie selection after input reversal, bounded provenance and no PUT execution.
Annotations/doc-derived domains are explicit assumptions, not runtime proofs.

All copied v2 originals match their copy hashes; original162-card corpus digest
is unchanged. The new source freeze still matches implementation. Default public
API remains v2; v5 requires explicit `retriever="v5"` / `--retriever v5`.

Stop at this recorded outcome: no expanded benchmark, paid inference or silent
retuning to manufacture a gain. The repository now has a reviewable fact-based
variant and an honest negative comparison. Further semantic-contract validation
would require a distinct registered change rather than reusing these scores.

[Per-task results](evaluation_v5/RESULTS.json) · [Freeze](evaluation_v5/FREEZE.json)
· [Engineering review](REVIEW.md) · [Protocol](PREREG.md)

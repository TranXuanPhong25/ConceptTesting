# V7: implementation, owner delivery audit and local embedding verification

2026-10-29. P3 engineering implemented; P0/P1 saved-generation audit completed.
No new Qwen/paid calls, target execution or final v85 grading by this work.
Original corpus, V2/V5/V6 sources/results and owner snapshot preserved.

## V85 evidence changes next-step priority

Portable artifacts are now available. Verified archive/imported8583hashes,
113preparation hashes and113complete generation pairs. An independent reviewer
reproduced counts and source/mutant examples.

| Gate | Delivered cards | Round1 gate hit | Round2 targeted | Card targets with delivered round2 input |
| --- | ---: | ---: | ---: | ---: |
| Line reachability only | 206 | 204 | 2 | 1 |
| Existing v11 gap | 69 | 51 | 18 | 15 |

These are card counts, not bugs/tasks. Round1 hits mechanically suppress round2
targeting. A line hit does not establish semantic-trigger coverage. Source-based
examples102/110 bind a card to a different expression/mechanism on the same line.
Restoring targeting is not automatically beneficial: the card itself may be wrong.

Only16retrieval tasks retain round2 inputs versus25v11 tasks; this is delivery,
not correctness/detection. New input expected outputs have not been graded here.
At audit observation owner STATUS was blocked RuntimeError, with no
HANDOFF_COMPLETE.json. No attempt was made to diagnose/restart its controller.

Cached v6 selections share exact input source113/113; only17keep the identical
ordered card/site list. Full original v11 candidate pool is missing from portable
checkpoint, so an exact offline rebind is unavailable. Selected targets alone
cannot reconstruct the pool. [Full audit](owner_audit/REPORT.md).

## What is implemented

- Independent full-corpus BM25 and dense recall, fused with structural candidates;
  RRF60,12unique candidate IDs, maximum3outputs.
- Four controls: current/revised card descriptions × sparse/hybrid channels.
  Same source-ordered lexical binder and AST-type restriction across arms.
- Eight conditional concept records in seven families. Pinned documentation
  citation/hash/span validation, contract/flow/domain obligations, benign contrast.
  No historical bug/fix corpus claim; no target obligations automatically satisfied.
- Dense-only nomination remains tier0/unknown. Binding quotes public contract and
  exact source spans but does not establish alignment, feasible trigger or oracle.
- Explicit site-cap64, character-cap and runtime-token512 truncation reporting.
  Cache model/text identity, vector shape/finite/norm validation; no silent fallback.
- Separate packet export preserves source/effect/requirements for a later controlled
  v11 integration. Existing v85 source and frozen experiment are unchanged.

## Actual embedding verification

Pinned Jina base-code ONNX revision516f4baf13dec4ddddda8631e019b5737c8bc250,
FastEmbed0.9.1, CPU2threads/batch8, mean pooling/L2, no prefixes,512runtime tokens.
Model/tokenizer hashes in MODEL_MANIFEST.json; weights outside repository.

After independent review and prospective fixes, four predeclared authored source
fixtures ran A/B/C/D:16packets complete,522new text embeddings,474cache reads,
0token-truncated texts,30.26seconds. Source/config freeze unchanged during run.
[Raw source freeze/results](engineering_smoke_20261029/RESULTS.json).

This confirms real local inference, independent nomination, caching and output
statuses. Smoke rankings remain exploratory engineering observations. They contain
irrelevant unknown candidates and do not establish reliable semantic applicability.
For example, the distinct-cardinality fixture still returns multiplicity risk
hypotheses; no gate/opportunity is called a confirmed bug. We did not tune rules,
weights or choose another model after inspecting these rankings.

23new engineering tests pass:8evidence,13hybrid,2cache checks. CLI evidence validation
passes; combined with6existing public-API checks the final suite passes29/29.
Independent pre-outcome review and amendments in REVIEW_V7/PREREG_V7.
No benchmark precision, generalization, v85 improvement or test-generation efficacy
is measured by these checks. Inherited V6 outcomes live in PARENT_V6_RESULTS.md.

## What remains

1. Recover original full v11 tool pool or explicitly design a new gate-binding
   variant; do not pretend the selected portable targets are the pool.
2. P4 independently reviewed fixed semantic diagnostic, including benign controls;
   no dense/base GO verdict yet.
3. Measure v2/v6/dense selection separately from gate/delivery repair, holding
   generator/model/oracle budget fixed in a new integration version.
4. Future corpus work needs externally verified real bug/fix exemplars; this
   iteration improves documentary specificity only.

Next strongest concrete signal is gate/delivery alignment from the saved v85
audit, alongside the ready independent retrieval channels. The owner run remains
managed by its original session.

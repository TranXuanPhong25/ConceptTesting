# VR14 — concept-template query diagnostic, 2026-10-30

Prototype complete. A structured concept query recovers more of this small KB's
bindable templates than raw source, but relation benefits and test-generation
quality remain unproven. Do not promote it to the default or the v11 pipeline.

## What changed

Source-only extraction produces reusable neutral concepts with concrete source
roles, conditional properties and evidence spans **before retrieval**. One query
retrieves up to three of nine templates; a shared binder instantiates their input
partitions. Unknown domains/flows abstain. No inferred concept is a defect verdict.
Requirements remain separate and unverified; partitions are plans, not observations.

All three arms use the same copied vr13 SQLite FTS5 BM25/tokenizer, corpus,
extractor and binder. `relations` adds composite concept names and edge text to
`concepts`; it is not an edge-only ablation. The KB vocabulary intentionally matches
the extractor, which makes this an interface diagnostic rather than an independent
test of semantic retrieval quality. See [PREREG](PREREG.md) and [review](REVIEW.md).

## Authored development fixtures

18 fixtures contain 16 expected concept instances and three expected relations;
some fixtures are benign or deliberately unsupported. These are authored engineering
checks, not held-out benchmark tasks.

| Measure | Raw source | Primitive concepts | Concepts + relations |
| --- | ---: | ---: | ---: |
| Expected template present among top 3 | 10/16 | 16/16 | 16/16 |
| Exact source-slot and relation binding | 10/16 | 16/16 | 16/16 |
| Expected edges in exact bindings | 0/3 | 3/3 | 3/3 |
| False bindings / slot errors / relation errors | 0/0/0 | 0/0/0 | 0/0/0 |

The extractor produced the same 16 instances in every arm. Missing edges for raw
are retrieval omissions, not three incorrect edges. The primitive query can still
retrieve a composite template, and the common binder sees relations in every arm;
therefore even these fixtures show **no incremental benefit from the relation query**.

## Unlabeled census of all 113 saved V85 buggy sources

| Measure | Raw source | Primitive concepts | Concepts + relations |
| --- | ---: | ---: | ---: |
| Tasks with any extracted instance | 67/113 | 67/113 | 67/113 |
| Tasks with any returned binding | 56/113 (49.6%) | 67/113 (59.3%) | 67/113 (59.3%) |
| Bound instances / extracted instances | 98/131 | 131/131 | 131/131 |
| Extracted relation edges | 0 | 0 | 0 |
| Source-processing errors | 0 | 0 | 0 |
| Queries truncated at 2,048 characters | 1 | 0 | 0 |

The structured arms add binding coverage on 11 tasks and lose none: 10, 26, 36, 42,
51, 52, 73, 109, 135, 149, 161. This is **unlabeled coverage**, not correct-concept
recall, supported-binding precision or bug detection. Counts compare representations
within vr14; they are not comparable to old vr2/vr13 family-site metrics or V85 scores.

Extraction is shallow: 86 cardinality, 14 element-mapping, 11 direct-indexing,
11 deduplication, seven selective-filtering and two position-lookup instances.
No sequence-transform, frequency-aggregation or search-position-indexing instance
was extracted. In particular, cardinality accounts for 65.6% of all instances.
Both structured arms have identical queries on all 113 tasks because no relations
were extracted. The extractor leaves 46 tasks without any instance.

There are 192 explicit unknown records: 169 indexed receiver domains, nine text
replacement receiver domains, five search receiver domains, five effectful/multiple
predicates, two nested comprehensions, one source flow and one destructured iteration.
These are records, not distinct tasks or measured extraction mistakes. Strict type
boundaries protect against inventing semantics but sharply reduce real-code coverage.
None of the 113 public docstrings matched the four narrow requirement directives;
the requirement parser supplied no cue in this census.

## What this establishes, and what it does not

The concept → query → template → binding → partition interface works on its authored
cases and is inspectable end to end. It is more concept-centric than querying only
spec/AST text. ConceptCoder motivates reusable semantic concepts versus concrete
instances; this is a hand-written behavioral abstraction, not its trained concept
bottleneck, vocabulary, supervision or a reproduction of its performance.
Most extracted concepts here remain operation-level (especially cardinality),
below the richer algorithmic/design compositions sought in the original direction.
See the earlier [ConceptCoder definition audit](../../research/conceptcoder_20261027/V85_DEFINITION_AUDIT_20261029.md).

The result does not show that BM25 is needed: this nine-template KB has one template
per recognized kind, and every census task has at most three distinct recognized
kinds. A direct kind-to-template lookup would recover the same extracted instances.
The perfect 131/131 retention is therefore not evidence of a solved retrieval problem.
There is also no measured relation-query gain, whole-program preservation proof,
partition reachability, expected-output quality, bug-detection lift or token saving
in the v11 loop. All 20 engineering tests pass, but tests do not fill these evidence gaps.

The next useful change, if pursued, is bounded receiver/type and value-flow inference
with explicit public-spec evidence, evaluated against negative examples, to recover
meaningful compositions on real sources. Task51 shows why: its filter is bound, but
the preceding space replacement remains unknown. Do not relax abstention simply to
raise coverage. Before any downstream run, compare template routing against direct
kind lookup and validate whether partitions yield distinct, valid inputs. This report
does not authorize or launch another version or full113 test generation.

## Artifacts and cost

- [Walkthrough](WALKTHROUGH.md): task51 plus an authored search-to-index example.
- [Machine-readable results](evaluation/RESULTS.json), [sealed predictions](evaluation/PREDICTIONS.json).
- [Cohort provenance](CENSUS_PROVENANCE.json): all113 prepared file hashes match their parent freeze.
- [Final source freeze](FREEZE.json), [independent approval](REVIEW_APPROVAL.json), [completion hashes](evaluation/COMPLETE.json).
- Python 3.11.15, SQLite version recorded in RESULTS.json; no new dependency.
- **0 model calls, 0 LLM tokens, 0 target executions, no canonical use.** No running job.

Source/templates/labels were frozen and independently approved before diagnostic
execution. Predictions were sealed before fixture-label joining. No post-result
retuning or rerun was performed; the first rejected pre-outcome freeze is retained.

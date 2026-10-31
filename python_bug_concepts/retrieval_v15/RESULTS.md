# VR15 — domain evidence and concept composition, 2026-10-30

The representation weakness is partly repaired: the extractor adds 16 instances
and five source relations across three real development tasks, including the
previously missing replacement→filter relation in task51. BM25 still adds no
binding coverage over direct kind routing. No downstream test-generation gain
has been measured.

## Change and validation

Copied vr14 into a separate version; preserved its frozen sources/results. Domain
inference now follows qualified generic annotations, explicit parameter-linked
public type statements, builtin constructors, string-result operations and slices.
Every inferred domain retains source evidence and conditional assumptions. The
self-assignment resolver uses the value before assignment for RHS receivers.
Branch ambiguity, non-Name rebinding, walrus writes, unpacked search arguments,
shadowed constructors and conflicting annotations have explicit safeguards.

Two new neutral templates compose operations: `transform_then_filter` and
`distinct_cardinality`. They distinguish preprocessing from local selection and
distinct-counting from total-counting. They do not infer a defect or oracle.
Direct kind routing uses the same11templates, extractor/binder and candidate cap3,
prioritizes relational templates, places cardinality last and breaks ties by ID.
All BM25 arms share the2048character/128unique-term query limits.

33 engineering tests passed. Independent review approved all15 frozen dependency
hashes before outcomes, including the saved vr14 predictions used for comparison.
Predictions were sealed before fixture labels were joined. No post-result tuning.

## Source-only census: all113 saved public buggy sources

| Extractor measure | VR14 | VR15 |
| --- | ---: | ---: |
| Tasks with instances | 67 | 69 |
| Instances | 131 | 147 |
| Cardinality instances | 86 | 86 |
| Non-cardinality instances | 45 | 61 |
| Relation-bearing instances / edges | 0 | 5 |
| Tasks with a relation | 0 | 3 |
| Explicit unknown records | 192 | 180 |

All131 old instance IDs remain;16 new instances occur on eight tasks:8,20,37,48,
51,74,137,158. Two tasks newly acquire instances/bindings:8 and137. No prior instance
is removed. The five edges are one transformation→selection edge, one corresponding
composite edge, and three inline deduplication→count edges. They are not five
independent tasks: task51 has two edges for one composition; task74 has two count
sites; task158 has one count site.

The16additions are six sequence transformations, five direct indexed reads, one
position lookup, one transform/filter composite and three distinct-count composites.
Cardinality still dominates (86/147,58.5%);44tasks remain without any concept. There
is still no search-position-indexing or frequency-aggregation instance on the census.

| VR15 routing arm | Tasks with bindings | Bound instances | Tasks with bound relations |
| --- | ---: | ---: | ---: |
| Raw source BM25 | 54/113 | 100/147 | 2 |
| Primitive concept query | 69/113 | 147/147 | 3 |
| Concepts + composites + relations | 69/113 | 147/147 | 3 |
| Direct kind lookup | 69/113 | 147/147 | 3 |

There is **no incremental coverage benefit from relation query text or BM25 over
direct routing**. Structured queries now differ on3tasks; they remain identical on
110/113. Every task has at most3recognized kinds, so the three-template cap never
forces direct routing to choose among more applicable kinds. This small aligned
KB is not a retrieval-generalization benchmark.

Raw coverage drops56→54tasks versus vr14: gains51/137, losses19/50/126/132. In those
four losses, new composite templates enter the top3 and displace the old bindable
primitive template. This negative is retained. Cross-version routing comparisons
change both extraction and KB; the within-vr15 table shares both.

All arms have0processing errors. Raw has one character-truncated query and zero
term-truncated queries; the other BM25 arms have neither. Direct does not use its
informational query for ranking. Domain evidence counts are receipt occurrences,
not independent tasks: the public-type rule is used only for task51, though it
appears in five slot receipts. Behavioral requirement cues remain separate; this
change does not extract general natural-language requirements.

## Engineering fixtures and semantic interpretation

The18authored fixtures now label18expected instances and five edges (two composite
labels added prospectively). Exact slot+relation bindings: raw10/18; primitive,
relational and direct18/18. No false binding, slot or relation errors against these
authored labels. This measures implementation behavior on development examples,
not heldout semantic precision.

All five relation-bearing census instances received independent source review:
conditional support5, contradicted0, unknown0. Task51's explicit public string type
supports the replacement semantics and the assignment feeds the filter. Tasks74
and158 contain literal inline `len(set(...))` expressions; their domain evidence
receipts are empty, but builtin semantics conditional on valid inputs support
distinct counting. Reviewer also reads their public list-of-strings contracts.
This is method-aware source review, not execution, calibrated precision or five
independent successes. See [semantic review](SEMANTIC_REVIEW.json).

An additional descriptive audit covers all16new instances across eight tasks,
including the12primitive additions: conditional support16, contradicted0, unknown0.
The reviewer verified134source evidence spans and the complete new-instance export
against sealed deltas. The131unchanged instances were not re-reviewed. This audit
also identifies a real limit: task37's needle comes from the searched list, so an
absent-needle partition may be unreachable. Supported concept semantics do not make
every generic partition feasible or useful.

## What is improved and what remains weak

Vr14 could name local filtering at task51 but could not connect its input to the
preceding replacement. Vr15 now records both stages, concrete role bindings and
joint input partitions. This makes the concept more useful for designing tests:
consider pattern presence together with retained/removed elements, rather than
only asking whether the local filter executed. [Full walkthrough](WALKTHROUGH.md).

These concepts remain hand-written operation compositions, not ConceptCoder's
trained design-concept bottleneck. The benefit shown here is richer, evidence-backed
representation. Input construction, partition reachability, oracle correctness and
bug detection remain unmeasured. Direct routing suffices for current templates;
there is no reason from these results to add a larger encoder or promote BM25.

The180unknown records include163unknown indexed receivers. Public type grammar is
deliberately narrow and source-specific development exposure includes task51. Domain
inference is bounded and conditional, not a general type checker or flow proof.
No automatic v11 integration, new version, full113test-generation or default change.

Artifacts: [source freeze](FREEZE.json), [review](REVIEW.md), [results JSON](evaluation/RESULTS.json),
[sealed predictions](evaluation/PREDICTIONS.json), [instance delta](evaluation/DELTA_VR14.json).
Diagnostic cost:0model/APIcalls,0target executions, no canonical use; no active job.

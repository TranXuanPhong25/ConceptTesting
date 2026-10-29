# V7 conditional mechanism evidence overlay

This overlay improves the specificity and auditability of eight existing cards.
It does not add a verified bug corpus, prove target applicability, execute a
target, or establish a retrieval or test-generation gain. Existing cards,
source/vendor files and frozen results remain unchanged.

## Scope and representation

`data/mechanism_evidence.json` contains eight records in seven families:

| Existing card | Mechanism family |
| --- | --- |
| `py.set-loses-multiplicity` | `required-multiplicity-lost` |
| `py.presence-frequency-confusion` | `required-multiplicity-lost` |
| `py.unicode-text-byte-domain` | `text-domain-mismatch` |
| `py.first-match-vs-optimum` | `premature-selection` |
| `py.extremum-initial-sentinel` | `sentinel-outside-selection-domain` |
| `py.empty-reduction-domain` | `derived-domain-empty` |
| `py.text-normalization-contract` | `required-text-distinction-erased` |
| `py.mutable-default` | `cross-call-state-leak` |

Each record separates the concrete operation realization from its causal effect,
affected consumer and admissible distinguishing-input class. Contract, flow and
domain requirements each state what target evidence is needed. Exclusions and
benign contrasts describe when the operation can be appropriate. These are
review obligations, not newly implemented static checks or satisfied predicates.

The two multiplicity cards share a family but are not interchangeable bindings.
`py.set-order-loss` keeps its own identity: loss of ordering is a different effect.
The set-loss overlay refines only the multiplicity branch of the original card;
a duplicated literal hiding a missing distinct entry still needs separate
specification evidence. The original card is not rewritten or relabeled.

All eight records have `evidence_status=curated_conditional_template`. The loader
adds `binding_status=unknown_requires_target_evidence` to every requirement.
No expected output, target bug label or satisfied-condition assertion is supplied.

## Evidence and its limits

Citations resolve to existing pinned Python documentation through original and
extension pattern IDs. The loader checks each cited source against its existing
manifest revision and SHA-256, verifies the local file hash and line span, and
requires the quote to occur inside that span with whitespace normalized.
Returned citations include resolved path, revision, span, hash and upstream URL.

These checks establish source integrity and quoted text. They do not establish
that a curated inference follows from the quote or applies to a target. Each
citation states its limited claim explicitly: for example, the max documentation
establishes largest-item semantics, not a bug in a particular early return.
The normalization citation directly covers lower/lstrip, not every possible
normalization API.

Benign contrasts are conceptual review examples. The mutable-default contrast
is grounded in the Python FAQ's intentional memoization example. None is claimed
to be a newly executed example or a mined historical bug/fix pair. No upstream
fix metadata was downloaded in this step; acquiring real bug/fix evidence remains
future work. No benchmark reference, gold label or target-specific example is
used in the overlay or loader.

## Integration API

```python
from python_bug_concepts.retrieval_v7.concept_evidence import (
    load_overlay, feature_views, family_for, digest,
)

overlay = load_overlay()  # validates afresh; reuse this mapping while indexing
old_views = feature_views(card, revised=False)
new_views = feature_views(card, revised=True, overlay=overlay)
family = family_for(card, overlay=overlay)
cache_version = digest()
```

Both view modes return three strings: `contract`, `mechanism` and `trigger`.
Original views use only the existing card's positive description, preconditions,
oracle and trigger templates. Revised views use the overlay's conditional
contract/domain requirements, realizations, causal effect, consumer/flow and
trigger. Uncovered cards return exactly the same views in both modes.

Exclusions, benign contrasts, citations and instructions for collecting evidence
are deliberately omitted from these positive retrieval views; they remain in
the overlay for separate applicability review. This prevents negative examples
from being silently indexed as positive matches. The original card's own positive
prose is retained as originally authored, including any qualifications it contains.
Embedding similarity to a conditional description must not promote its evidence
status. `family_for` supplies grouping metadata only; it does not change ranking,
deduplication or selection automatically.

`digest()` fingerprints this module, the overlay, card inputs, pattern registries
and source manifests for cache invalidation. Call `load_overlay()` before using
an index to verify actual cited files; a digest alone is not a file-integrity check.

## Verification

On 2026-10-29, the following engineering suite passed: **8 tests**.

```bash
python -m unittest python_bug_concepts.retrieval_v7.evidence_tests -v
```

Checks cover pinned citations, fabricated/out-of-span quotes, manifest and actual
hash mismatches, unknown source IDs, attempted proof-status promotion, duplicate
records, missing requirement roles, original/uncovered view stability, negative
evidence separation, family grouping and absence of input mutation.

The suite only reads local data and exercises the loader/view functions. No model
call, target execution, retrieval benchmark, oracle generation or efficacy scoring
was performed for this overlay task. V7 integration and any later evaluation are
separate work; these eight passing tests are not evidence of a scientific gain.

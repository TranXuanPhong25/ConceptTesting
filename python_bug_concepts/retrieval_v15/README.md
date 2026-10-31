# VR15: domains and composed behavioral concepts

Completed: [results](RESULTS.md), [task51 walkthrough](WALKTHROUGH.md),
[independent source judgments](SEMANTIC_REVIEW.json).

Public code/spec → conditional domain evidence → primitive/composite instances →
BM25 or direct template routing → source bindings and planned input partitions.

This isolated copy improves vr14's missing receiver domains and composed relations.
Two new templates distinguish transformation-before-filtering from local filtering,
and counting distinct values from counting occurrences. They do not assert a bug.
Public type statements, annotations and builtin-result rules carry source receipts;
unknown, shadowed or ambiguous flows still abstain. No new dependency or model.

```sh
/tmp/pytoy-v84-venv/bin/python -m unittest python_bug_concepts.retrieval_v15.test_engineering
/tmp/pytoy-v84-venv/bin/python -m python_bug_concepts.retrieval_v15 example.py --entry f --arm relations
```

Arms: `raw`, `concepts`, `relations`, `direct`. All share the11templates, extractor,
binder and three-candidate cap. Direct lookup prioritizes relation-bearing templates,
puts cardinality last and breaks ties by ID; it measures the need for lexical search
in this small aligned KB. It is a routing-policy control, not a matched query arm.

Explicit public type cues support Sphinx `:type parameter: str`, parameter headers
`parameter (str): ...`, and a single-parameter sentence of the form
`function_name is a function that takes string and returns ... .`
This last grammar applies to any function name, not a task ID. Cues are unverified
contract assumptions; general prose, examples and arbitrary method names are not
type evidence. Runtime types and partition reachability are never proven.

The source-only diagnostic is registered in [PREREG.md](PREREG.md). Engineering
fixtures and the113exposed sources do not measure heldout precision or test-generation
efficacy. No v11/default integration, paper reproduction or automatic downstream run.

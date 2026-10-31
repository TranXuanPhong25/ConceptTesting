# VR14 concept-template query prototype

Completed diagnostic: [results](RESULTS.md), [end-to-end examples](WALKTHROUGH.md).

Public code/spec → conditional concept instances → one BM25 query → top-three
templates → typed source-slot binding → planned input partitions.

Nine neutral templates cover filtering, multiplicity and search/indexing plus
neighboring operations. This changes the query representation before retrieval;
it does not reproduce ConceptCoder training. Source concepts can occur in correct
code. Requirements, observed structure and test obligations remain separate.

```sh
/tmp/pytoy-v84-venv/bin/python -m unittest python_bug_concepts.retrieval_v14.test_engineering
/tmp/pytoy-v84-venv/bin/python -m python_bug_concepts.retrieval_v14 example.py --entry f --arm relations
```

Use Python 3.11 with LibCST and SQLite FTS5 (existing project environment); no new
dependency. Arms `raw`, `concepts`, `relations` share the KB, extractor, binder,
top-three cap, 2,048-character and inherited 128-unique-term query limits. Relations
adds both composite concepts and edge text; this is not an edge-only ablation.
Templates deliberately use the extractor's vocabulary, so authored-fixture gains
would show an interface working, not unbiased retrieval generalization.

`PREREG.md` fixes the diagnostic. `prepare_census.py` copies only public fields from
all 113 hash-verified saved V85 prepared records. After independent review and
freeze, `python -m python_bug_concepts.retrieval_v14.diagnostic run` writes one
evaluation and refuses to overwrite it. Engineering fixtures are development
checks; the 113-task census measures unlabeled coverage, not semantic precision.

The bounded lexical analysis is not a control-flow proof or a type checker.
Partitions are plans, not generated tests, reachability evidence or expected
outputs. No model, canonical implementation, target execution, v11 integration
or public-default change is part of this prototype.

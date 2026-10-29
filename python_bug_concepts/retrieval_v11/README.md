# vr11 operation-grounded concept retrieval

```python
from python_bug_concepts.retrieval_v11.hybrid_engine import Retriever
from python_bug_concepts.retrieval_v11.dense import Encoder

# A/C need no encoder. B/D use the same pinned local Jina CPU model as V7.
r = Retriever(encoder=None)  # G: operation binder, legacy query, no family dedup.
packet = r.search(code=public_source, arm="A", top_k=3)
r.close()
```

`results` may contain fewer than3hypotheses. `source_supported_hypotheses` and
`test_opportunities` partition returned proposals by existing local support;
neither category asserts a bug. `screened_bindings` records required-operation
absence, unknown role, or explicit public-contract contradiction.

Control: `binder_policy="legacy"`. Optional Q: `query_strategy="coverage"`;
optional F also sets `family_diversity=True`. Register these separately before
outcomes; the default isolates the new binder with the old candidate/query setup.

Run source-only engineering checks using the established V7 environment:

```bash
python_bug_concepts/retrieval_v7/.venv/bin/python -m unittest python_bug_concepts.retrieval_v11.engineering_tests -v
```

No target program is executed, and no embedding inference is used by these checks.
Independent review and a new freeze are required before a diagnostic run. Old
vr10 source-review errors informed this development version; they cannot serve
as independent confirmation of its quality.

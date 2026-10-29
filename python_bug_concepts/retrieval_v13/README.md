# vr13 role completeness

```python
from python_bug_concepts.retrieval_v13.hybrid_engine import Retriever
r = Retriever()  # same G operation policy, legacy query, family dedup off
packet = r.search(code=public_source, arm="A", top_k=3)
r.close()
```

B/D require the unchanged pinned local encoder from `.dense.Encoder`. Runtime
API matches vr11. Only fixed repeated-literal replacement and direct lexical
self-recursion role coverage changed; operation support remains conditional.

```bash
python_bug_concepts/retrieval_v7/.venv/bin/python -m unittest python_bug_concepts.retrieval_v13.engineering_tests -v
```

All26checks are authored source-only engineering controls. No target execution,
model inference or efficacy scoring. Read PREREG.md before a new evaluation;
independent review and frozen source approval are required. Previously inspected
vr10/vr11 data must be reported as development regression when reused.

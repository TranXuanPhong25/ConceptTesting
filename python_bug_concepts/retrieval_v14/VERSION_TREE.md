# Retrieval development tree — 2026-10-30

```mermaid
flowchart TD
    V7["V7: BM25 + dense + source-site binding"] --> VR10["vr10 dense diagnostic: 0 new supported bindings"]
    V7 --> VR11["vr11: operation/role binder"]
    VR11 --> VR13["vr13: 9 supported retained; contradicted 22→14; known sites 8→7"]
    VR13 --> VR14["vr14: concept instances BEFORE query; slots + relations → partitions"]
    V2["V2 compact cards"] --> V85["V85 inside v11: full113 ref78 vs77; no clear gain"]
    V85 --> VR8["vr8 strict gates: all6/6 R1 ceiling"]
    VR8 --> VR9["vr9 retention: all6/6; no gain"]
    VR9 --> VR12["vr12 expanded11: ref9 vs generic8; no applicability gain shown"]
```

Vr14 reuses vr13's parser metadata and lexical backend. Its new query is built
from neutral semantic instances, not raw AST expression text. Typed roles bind a
retrieved template to source evidence and planned input partitions. This is a
representation prototype, not a downstream v11 test-generation integration.

ConceptCoder informs the distinction between reusable concepts and concrete
measurements/instances. No trained bottleneck or paper implementation is reproduced.
See [RESULTS.md](RESULTS.md) for authored-fixture checks and separate unlabeled census.
Neither metric is a bug-detection score. Old frozen experiments remain unchanged.

# Retrieval development tree, 2026-10-29

```text
V7: open BM25 + independent dense + structural candidates, source-site binder
├── vr10: fixed 28-query diagnostic → NO_GO for dense incremental supported recall
└── vr11: operation/effect roles + abstention, no forced three proposals
    └── vr13: repeated-literal replacement + direct-recursion role completeness

V85: V2 cards inside LineFacts v11 loop, complete113; ref78 vs77, p=1.0
└── vr8: exact semantic OBS gates, hard filtering → 6/6 R1 ceiling, no gain
    └── vr9: applicability routing + valid non-hit retention → 6/6 ceiling, no gain
        └── vr12_expanded: 11 fresh eligible tasks, K1/four arms → preflight blocked
```

Vr11/vr13 change source binding, not the fixed candidate retrieval model.
They are exposed-source development checks and are not integrated into VR12.
Vr11 cuts arm-A buggy proposals36→25 with known-site hits8→6; vr13 returns26
with7/8hits. Final source review gives V7/vr13 9/9supported and22/14contradicted
bindings. Canonical proposals36→18, still18contradicted: semantics remain weak.

Known-site hit = the concept's first returned evidence line matches an old
annotated site, not proof of bug detection. Supported/contradicted = method-blind
agent source judgment, not a calibrated classifier or final oracle result.
OBS-uncovered = no observed true gate state on saved valid round1inputs, not a bug.
K1 = one registered generation replicate, not one input or one HTTP request.

No new paper method was reproduced. Jina embeddings are the unchanged local
encoder; LibCST supplies lexical bindings. ConceptCoder's concept-versus-measurement
distinction informs terminology only, not its trained model implementation.

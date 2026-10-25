# Version relationship

```text
v7 packaged baseline
|-- v31 fault templates -> v34 placebo -> v35 fixed-pool ceiling
`-- v57 pathfault
    |-- v60 native -> v61 integration -> v62 contract fix -> v63 scope guard
    |                                                  `-- v65 evidence gate repair
    `-- v64 symbolic path (independent branch; unchanged here)
```

v31 retains original18/33 vs plain15/33; concept attribution remains weak.
v63 completed six-case pilot with provisional concept0/6, plain0/6, pattern1/6.
v65 changes hypothesis admission, public checks, budget allocation, display
selection and gate enforcement. Only authored engineering checks have run.
No detection result; not a promoted best pipeline.

Concept: spec-versus-code fault hypothesis, still semantically unverified.
Witness: repeated concrete input exposing a difference to an alternative.
Gate: public-consistent alternative plus non-public sensitive witness in every
case's prepared prompt. Neither witness nor gate establishes bug truth.

Libraries: existing Python AST and Z3/native replay. No paper reimplementation.

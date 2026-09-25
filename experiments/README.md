# Concept-Guided C Test Generation Experiments

Five bounded, local research MVPs translate a different 2025/2026 paper idea
into the same basic question: can structured program concepts produce a test
that passes on the intended implementation and distinguishes a plausible
fault?

| Track | Concept-to-test mechanism | Local evidence |
| --- | --- | --- |
| STRUT | static C facts to a structured unit-test seed and assertion harness | kills an upper-boundary mutant |
| HGFuzzer | call path and path predicates to checksum-valid directed inputs | ASan failure on vulnerable fixture; fixed fixture rejects it |
| CKGFuzzer | API/state/constraint/sink graph to a valid call sequence | kills an invalid-state boundary mutant |
| G2FUZZ | binary-format constraints to invariant-preserving generators | 6 differential inputs in the deterministic smoke |
| LLAMAFUZZ | seed-pair delta plus input relations | kills a length-guard boundary mutant |

Run every smoke experiment:

```bash
python3 experiments/run_all.py
```

Each track is deliberately small and self-contained. The fixtures are local
teaching programs or controlled mutants, not external targets. Passing these
smokes is evidence that the experiment plumbing supports a differential oracle;
it is not a reproduction of the source paper's full benchmark or headline
numbers. The next research step is to replace the hand-authored facts with
`concept_annotator` output and run the strongest mechanisms against Magma's
existing vulnerable/fixed canary oracle.

# KITE concept extension

This package implements the reusable, testable parts of the KITE/MutGen protocol:

- KITE semantic mechanisms (`what`, `where`, `how`) and normalized AST-shaped unit structures;
- coarse-key/fingerprint/Jaccard dual retrieval, injection plans, four validity gates, and promotion gates;
- MutGen-compatible PIT report tuples and prompts for surviving/uncovered mutants;
- explicit concept records with violated constraint, applicability, trigger relation, and expected oracle;
- equal per-task call budgets, durable SQLite checkpoints, fixed-pass/buggy-fail re-execution;
- RBDR, project-level RBDR, paired bootstrap confidence intervals, and exact McNemar tests.

The implementation uses only the Python standard library. Java parsing is a documented lexical
reconstruction because KITE did not release its Java parser, prompts, dataset manifest, or code.

## Safety and environment

Never place checkouts in this repository. Set an external cache directory and source the existing
Vertex configuration before an LLM run:

```bash
export KITE_CACHE=/tmp/kite-concept-cache
source /home/phong/dev/ConceptTester/scripts/vertex_env.sh
source /home/phong/.local/kite/env.sh
```

`~/.local/kite/env.sh` selects JDK 11 and Defects4J. The system Java 21 remains appropriate for
ordinary Maven work. The package's LLM adapter delegates to `magma.llm_client.make_llm`; it refuses
non-Vertex or non-Gemini-3-Flash-preview configurations.

## Utilities

```bash
python -m kite_concept.cli parse-pit CHECKOUT/target/pit-reports --out "$KITE_CACHE/pit.jsonl"
python -m kite_concept.cli tuning-subset manifest.json --size 40 --seed 260711573 --out tuning.json
python -m kite_concept.cli score results.jsonl --left concept --right mutgen
python -m pytest -q tests/test_kite_concept.py
```

The checkpoint key is `(task_id, arm)`. Completed arms are reused, failures remain inspectable, and
each LLM invocation must call the supplied `charge` callback before another invocation is allowed.


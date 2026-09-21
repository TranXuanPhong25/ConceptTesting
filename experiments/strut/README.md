# STRUT MVP: structured C test seeds

This is a bounded, local reproduction of STRUT's central idea, not a reproduction of its full C benchmark or reported scores. It combines a small static read of a C target with ConceptCoder-style hints, writes a structured seed, renders a C assertion harness, and checks a behavioral red/green oracle.

The fixture has `classify_window(value, lower, upper)`. The relevant concept is that equality at the upper boundary remains in-range. The controlled mutant changes `value > upper` to `value >= upper`.

## Run

```bash
python3 experiments/strut/run.py
```

Expected outcome:

```text
original_exit=0
mutant_exit=<non-zero>
PASS: original green; boundary mutant red
```

The generated artifacts are placed in `experiments/strut/out/` and are ignored by Git.

## Test

```bash
cd experiments/strut
python3 -m unittest -v test_structured_seed.py
```

## What is structured here

`fixture/concept_hints.json` represents the input that a fuller ConceptCoder/static analysis stage would supply: parameter types, guards, branch intent, expected oracle, and boundary cases. `structured_seed.py` adds facts it can recover locally from the target: function signature and comparisons. The renderer only consumes that seed; it does not inspect the mutant.

## Limits

- This uses a deterministic toy C target and a single controlled boundary mutant.
- It does not invoke an LLM, a live service, a real vulnerability, Docker, Magma, or a full fuzz campaign.
- A passing original and failing mutant demonstrates one valid fault-detecting test, not STRUT's paper-level coverage or execution-pass results.

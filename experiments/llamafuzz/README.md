# LLAMAFUZZ-Inspired Structured Mutation MVP

This is a small, local reproduction of one useful LLAMAFUZZ idea: learn a
structure-preserving mutation from seed pairs rather than mutate arbitrary
bytes. It is a defensive test-generation fixture, not a vulnerability target
and not a fuzzing campaign.

## What runs

`seed_pairs.json` records two valid `MSG|DECLARED_LEN|PAYLOAD` mutations. The
concept record supplies the format invariant and the target guard. The runner:

1. selects the pair labeled `guard_hit`;
2. transfers its field-level delta to `base_seed`;
3. repairs `DECLARED_LEN` to preserve `declared_len == len(payload)`;
4. compiles two local C programs with Apple/LLVM `clang`;
5. checks the generated input on both programs.

The only difference between the programs is a controlled boundary mutant:
`declared_len >= 7` becomes `declared_len > 7`. The result is useful only if
the same well-formed input hits the original guard and distinguishes the mutant.

## Run

From the repository root:

```bash
python3 -m unittest discover -s experiments/llamafuzz/tests -v
python3 experiments/llamafuzz/structured_mutation.py
```

The runner uses a temporary build directory and writes the deterministic record
to `experiments/llamafuzz/results/smoke.json`.

## Observed local smoke result

On this host (Apple clang 17), the generated candidate is
`MSG|7|MAGMA!!`. It is well-formed, returns `GUARD_HIT` on
`packet_original.c`, and returns `ACCEPT` on `packet_mutant.c`.

## Relationship to the paper and this repository

LLAMAFUZZ trains on mutation seed pairs to retain structure in complex inputs,
then delegates exploration to a greybox fuzzer. This MVP implements only the
first, inspectable part. `concept.json` is deliberately the extension point:
in a Magma-scale run, its fields could come from the existing static annotator
and describe file grammar, cross-field dependencies, parser state, and a
target-reachability condition.

It does not reproduce the paper's trained model, AFL++ loop, Magma corpus, bug
counts, or coverage claims. Full Magma campaigns are intentionally out of scope
for this bounded smoke; they require the repository's Docker/x86 setup and a
separate time budget.

## Files

- `structured_mutation.py`: seed-pair delta, invariant repair, compile/run oracle.
- `concept.json`: static concept hint and input relation.
- `seed_pairs.json`: deterministic local seed-pair corpus.
- `fixture/`: original and boundary-mutant C harnesses.
- `tests/`: unit and red/green integration checks.
- `results/smoke.json`: checked result from the bounded run.

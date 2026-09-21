# CKGFuzzer-Inspired Local MVP

This directory is a deliberately bounded reproduction of the CKGFuzzer idea:
use a code knowledge graph to select a state-valid C API sequence that reaches
a target sink and encodes a behavioral oracle. It is a local toy fixture, not
a vulnerability scanner and not a live-target fuzzer.

## Concept-to-harness shape

`graph.json` records five facts normally recovered from program analysis:

- API entry point: `ledger_create`.
- State transitions: construction opens a ledger; `ledger_add` supplies a
  staged amount; `ledger_commit` closes it.
- Argument constraint: the target boundary is `amount = 0`.
- Sink and guard: `ledger_commit` must reject `staged_amount <= 0` with `-2`.
- Fault model: changing `<=` to `<` accepts an empty commit.

`generate_harness.py` validates state preconditions before emitting a harness.
The harness contains only public API calls and the public result contract; it
does not inspect source code or refer to the mutant.

## Run

From the repository root:

```bash
python3 -m unittest discover -s experiments/ckgfuzzer/tests -v
python3 experiments/ckgfuzzer/run_experiment.py
```

The runner uses Apple/LLVM `clang`, compiles two local fixture variants, and
has a three-second execution limit per binary.

Expected outcome:

```text
original: returncode 0 (PASS)
mutant: non-zero returncode (FAIL at the generated assertion)
```

The generated `build/ledger_harness.c` must pass against `fixtures/ledger.c`
and fail against `fixtures/ledger_mutant.c`. That pass/fail pair is the local
fault-discrimination evidence, analogous to a mutation-kill check.

## Limitations and next step

This is not a reproduction of CKGFuzzer's full static-analysis and greybox
fuzzing pipeline. The graph is hand-authored for a deterministic fixture, and
the argument candidate is a single boundary value rather than an LLM-generated
seed. The intended next replacement is to populate this schema from
`concept_annotator`/CodeQL-style facts, then enumerate or LLM-rank candidate
arguments while retaining this compile-and-discriminate oracle.

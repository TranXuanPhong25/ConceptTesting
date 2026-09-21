# G2FUZZ-inspired structured-input MVP

This is a deliberately small, local reproduction of the part of G2FUZZ that
matters for concept-guided generation: a structured input specification creates
valid non-textual seeds, then mutations preserve format invariants before a
conventional executor consumes them. It is research plumbing, not a claim of
reproducing G2FUZZ's full LLM or fuzzing campaigns.

## Design

`generator.py` maps a static concept to a binary `G2FZ/v1` file:

| Concept fact | Encoded field |
| --- | --- |
| target guard is enabled | flag bit 0 |
| target path needs marker | payload prefix `BUG!` |
| required format facts | magic, version, length, checksum |

`mutate_valid` changes flags and payload bytes but rebuilds the byte length and
checksum. Thus every generated sample remains parseable by construction; this
is the essential difference from raw byte mutation for a binary parser.

`fixture_parser.c` is a deterministic local parser. Its `CONTROLLED_MUTANT`
build intentionally drops the required flag check. The experiment reports a
test only when the reference and mutant executables return different statuses.
That gives a bounded fault-detection signal without probing any external or
real-world target.

## Run

From repository root:

```bash
uv run python experiments/g2fuzz/run.py --mutations 16
uv run pytest experiments/g2fuzz/tests -q
```

The runner uses `clang` (or `cc`), compiles both local fixture variants in a
temporary directory, generates 3 concept seeds plus deterministic mutations,
and returns JSON. Exit code `42` means the local fixture's modeled target was
reached; it is not a crash or an exploit.

## Result on this machine

```text
uv run python experiments/g2fuzz/run.py --mutations 16
valid_inputs=19, target_hits=7, mutant_distinguished=6
```

The discriminator is the valid `BUG!` sample with the target flag disabled:
the reference returns `0`, whereas the controlled mutant returns `42`. The
target seed with flag enabled reaches `42` in both builds, confirming that the
concept can produce a target-valid structured input. The deterministic mutation
round generates the remaining six discriminators while preserving checksum and
length invariants.

## Limitations and next step

There is no LLM call, coverage-guided scheduling, corpus minimization, or
Magma campaign here. Those need a Linux containerized target and hours of
budget. The next integration should map `magma/concept_static.py` fields to a
per-format generator schema, seed the existing public Magma harnesses, and use
its vulnerable/fixed canary oracle rather than this controlled parser mutant.

# HGFuzzer-Inspired Local MVP

This is a bounded, defensive research demonstration of the central HGFuzzer
idea: a target-specific plan supplies a valid seed on the desired side of a
guard, and subsequent mutations preserve the facts required to keep reaching
that target. It only compiles and runs the deliberately vulnerable fixture in
this directory. It does not contact a network service, use an API key, or
target any real package.

## Concept Interface

[`concept_plan.json`](concept_plan.json) is the hand-authored equivalent of a
static-analysis/LLM handoff. It records:

- the local call path and target signal;
- the target branch `declared_len > 8` and the dangerous sink;
- packet grammar facts and a checksum relation;
- bounded campaign limits.

`run.py` builds the nearest boundary seed (`declared_len = 9`) and only mutates
payload bytes, recomputing the checksum. The plan therefore remains true for
every candidate, unlike blind byte mutation.

## Reproduce

Requires a local `clang` with AddressSanitizer support and Python 3. No Python
packages are needed.

```bash
python3 -m unittest discover -s experiments/hgfuzzer/tests -v
python3 experiments/hgfuzzer/run.py --smoke --cases 4 --timeout 2
```

Expected smoke properties:

- both binaries print `TARGET_HIT`, proving the directed plan reaches the
  target call path;
- the intentionally vulnerable fixture causes an AddressSanitizer report;
- the `-DFIXED` fixture reaches the same target then rejects the oversized
  payload without an AddressSanitizer report.

This produces a small local red/green oracle: the same concept-guided test
distinguishes the teaching fixture's vulnerable and repaired versions.

## Boundaries and Limitations

This is **not a reproduction of full HGFuzzer**. It omits target discovery,
interprocedural static analysis, LLM seed repair, AFL-style scheduling, real
library harnesses, corpus management, and coverage instrumentation. The
explicit `TARGET_HIT` signal is used because the local macOS toolchain exposes
`clang` but not `llvm-cov`. The result demonstrates experiment plumbing and a
concept schema, not a vulnerability-discovery claim.

The fixture intentionally overflows a stack buffer only under AddressSanitizer
in this isolated directory. Do not reuse it outside this controlled test.

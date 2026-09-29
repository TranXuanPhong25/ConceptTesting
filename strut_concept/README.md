# STRUT concept extension

This package implements a runnable, resume-safe three-arm experiment for C
function unit-test generation:

1. `direct`: Gemini writes C test code directly.
2. `strut`: static interface/context extraction → paper-style
   Inputs/Outputs/Stubs seed → Gemini structured cases → rule-based C.
3. `extended`: the same pipeline and call budget, adding atomic input
   constraints, branch fault hypotheses, and path-specific dependency effects.

The fixed substitute benchmark is a 40-function slice of Picolibc/Newlib's
string library.  The first 30 functions are the seeded tuning subset.  Sources,
prompts, generations, binaries, and gcov files are written only beneath the
chosen output directory, not this repository.

## Run

The default source root is supplied by TinyGo 0.41.1 on the evaluation machine.
On another machine, pass a Picolibc `newlib/libc/string` directory explicitly.

```bash
source /home/phong/dev/ConceptTester/scripts/vertex_env.sh
export LLM_PROVIDER=vertex
export LLM_MODEL=gemini-3-flash-preview
export VERTEX_LOCATION=global
export LLM_THINKING_BUDGET=0

python -m strut_concept tune \
  --output-dir /tmp/strut-concept-run \
  --picolibc-root /usr/lib/tinygo/lib/picolibc/newlib/libc/string

# Inspect/freeze tuning decisions, then add the remaining ten functions.
python -m strut_concept full --output-dir /tmp/strut-concept-run

python -m strut_concept report --output-dir /tmp/strut-concept-run --phase tune
python -m strut_concept report --output-dir /tmp/strut-concept-run --phase full
```

`results.jsonl` is an fsync'd append-only journal. Successful `(prompt version,
function, arm)` records are skipped on restart; generation failures are retried.
Raw responses and translated C remain outside the worktree. No credential or
environment value is persisted by the package.

Full-signature stubs are rendered as deterministic per-case dispatchers. Bare
callee names (where the conservative extractor cannot establish an interface)
remain normally linked; arbitrary stub signatures and C-expression values are
rejected.

## Metrics and statistics

Each generated suite is compiled with GCC coverage instrumentation and executed
with a timeout. The evaluator reads gcov JSON and restricts line/branch counts to
the focal function's source range. `report` emits function-level execution pass
rate, macro-averaged focal line/branch coverage, paired mean differences, a
10,000-resample paired bootstrap confidence interval, and an exact two-sided
sign test. Token usage metadata is retained per call.

## Scope

The public paper text specifies a richer industrial implementation based on
ANTLR/libclang and SunwiseAUnit. This package intentionally does not claim API,
artifact, or score compatibility with that unretrieved implementation. See the
dated research report for exact evidence and deviations.

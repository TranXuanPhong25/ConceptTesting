# MuTAP baseline

**Reimplementation/adaptation** of MuTAP (Dakhel et al., IST 2024) for TrickCatcher,
using the untouched original checkout in `vendor/mutap`, commit
`57c38c0c13df2c4d2b5714491e2c67a6d0463928`.

From the original code: exact `initalPromptGenerator`, `synxPromptGenerator`,
`synxtaxfixer`, `mutatePromptGenerator` and `generate_dialag` functions. The selected
family is normal/zero-shot with the authors’ chat dialogs. Spelling and wording
remain unchanged. Definitions are compiled without importing upstream transport or
running dataset-specific scripts.

Adapted driver:

1. Execute the provided base `check(candidate)` on the PUT. Abort on base failure.
   Generate a deterministic mutmut pool and screen it against **base tests alone**.
   Select at most N surviving mutants in mutation order; killed, error and timeout
   outcomes are retained separately and never targeted.
2. Generate initial tests using PUT, explicit spec/docstring (as comments) and base
   tests inside the original prompt. Syntax repairs use the original prompt and
   suffix truncation, bounded by the same global 8-call budget.
3. Normalize standalone assertions and apply the authors’ functional-refinement
   rule: execute against the PUT and replace wrong expected values with observed
   literal outputs. This step is reimplemented with AST parsing and serialization,
   rather than upstream line splitting and printed output. Raising calls are kept
   as diagnostic/export assertions, as upstream does, but excluded from the passing
   suite used for mutant screening. Timeouts and nonliteral outputs are dropped.
4. Rescreen selected survivors against base plus passing refined assertions. Query
   one untried surviving mutant, repair and merge the response, then rescreen. Stop
   at no untried selected survivors or the call ceiling. Every repair counts.
5. Export unique refined assertions in **generation order**, removing base copies
   and dropping beyond 20 with counts and dropped assertions recorded. A kill matrix
   and the authors’ greedy-selection rule are reimplemented as diagnostics only;
   they do not reorder or replace the registered comparison output. Original
   expected values remain in raw response and semantic-repair artifacts.

Mutation backend is required **mutmut 3.8.0**, using its source API for function and
class-method bodies. The requested setting specifies mutmut; the vendored artifact
actually uses **MutPy** in `MuTAP/Mutants_generation.py`, so this is an explicit
backend substitution, not a claim of identical upstream execution. Dependency/API
failure aborts with `mutation_failed`; no fallback mutation scheme is used.

`config.json` freezes K=3, 8 calls, 20 assertions, a mutation-pool cap of 32 and
**N = 7** base-surviving mutants. CLI option `--max-surviving-mutants` controls N;
`--max-mutants` controls the candidate pool before screening. Initial generation
plus seven augmentation calls fits eight; repairs consume the same allowance.
`n_mutants_generated`, `n_mutants`, `n_live_after_base`, `n_live_selected`,
`base_mutant_statuses`, `targeted_mutants` and mutation history distinguish stages.

Offline example from the repository root:

```bash
CoverUp_concept/.venv/bin/python -B -m trickcatcher_linefacts.baselines.mutap.run --tasks trickcatcher_linefacts/baselines/tests/dev_tasks.json --responses trickcatcher_linefacts/baselines/tests/dev_responses.json --out trickcatcher_linefacts/baselines/tests/another_mutap_run
```

CPU dry run on 2026-10-13, fake `ScriptedClient`, HumanEval development tasks,
K=3 (values below are **per sample**, identical across the three samples):

| Task | Entry | Calls | Exported assertions | Stop |
|---|---|---:|---:|---|
| 2 | truncate_number | 1 | 2 | Selected survivors exhausted |
| 3 | below_zero | 8 | 2 | N=7 selected mutants exhausted; additional base survivors excluded |
| 4 | mean_absolute_deviation | 5 | 1 | Selected survivors exhausted |

Totals: **9 output rows, 42 scripted calls, 15 assertions, 0 cap drops**. All base
suites passed, mutmut was used throughout, and at most seven survivors were selected
per sample. Outputs: `../tests/dry_runs/mutap/gen.jsonl`, manifest, task bundle and
complete prompt/response/mutant/refinement artifacts. `../tests/dry_runs/summary.json`
records environment and per-sample results. The shared suite passed **22 tests**,
including missing-mutmut failure, survivor limits, eight calls consumed by syntax
repair, generation-order truncation, class entries and offline transport isolation.

This verifies plumbing and the adapted loop, not real-model effectiveness. PUT-based
functional repair intentionally agrees with the PUT; common ref/full scoring is
necessary to measure spec correctness. Remaining work is a separately authorized
real-Qwen generation and scoring comparison. No endpoint call or held-out run was
performed. See `../README.md` for the common protocol and complete options.

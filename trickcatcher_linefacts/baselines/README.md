# CoverUp and MuTAP in TrickCatcher

These are **reimplementation/adaptation** baselines. CoverUp reuses the authors’
original prompt and coverage-improvement loop; MuTAP reuses the authors’ original
prompt functions and adapts the execution/refinement driver. See each baseline’s
README for provenance and differences. Author checkouts, SymPrompt and ACH stay
unchanged.

Inputs are a JSON bundle with `tasks`, each containing `task`, `entry`, `put`,
`base` (`check(candidate)`) and optionally `split`, `spec`, `docstring` or `prompt`.
Only these visible fields enter generation. An explicit specification takes
precedence; otherwise the entry’s docstring is used. Class methods require a
module-level entry wrapper. References, private tests, witnesses and concept facts
are excluded from prompts. The original task bundle is retained for later scoring.

Both runners use `common.py`: seeded requests, a shared OpenAI-compatible
`QwenClient` with model `qwen2.5-coder-7b-instruct`, artifact writing and AST
assertion extraction. Only explicit `--online` mode reads `QWEN_BASE_URL` and the
optional `QWEN_API_KEY`; neither value is stored or logged. There are no transport
retries. Default execution uses `ScriptedClient`, without endpoint configuration or
network calls. `--responses` supplies task-ID-to-response-list JSON; scripts reset
for each sample and repeat their last response. Without it, base tests are replayed
as a smoke test. `--replay` reads only the local Qwen cache and fails on a miss.

Defaults are frozen in each baseline’s `config.json`: **K = 3, at most 8 LLM calls
and at most 20 exported assertions per sample**. Syntax repairs and cache hits
count toward logical calls. CLI overrides may reduce either budget but cannot
exceed the protocol ceilings. Unique assertions are kept in generation order,
with normalized base-test copies removed. `n_assertions_uncapped`,
`n_assertions_dropped` and `truncated_assertions` record the generation-time cap.
Raw responses and accepted/refined raw assertions remain available for audit;
matched-count random-subset analysis is a later scoring step.

MuTAP also accepts `--max-mutants` (pool cap before base screening, default 32) and
`--max-surviving-mutants` (N base-surviving mutants, default 7). One initial request
plus at most seven augmentation requests fits the eight-call ceiling; syntax
repairs share that ceiling and may reduce augmentation requests.

Outputs match the committed SymPrompt/ACH row structure: `gen.jsonl`, `tasks.json`,
`manifest.json`, and per-sample artifacts. Rows include `task`, `arm`, `sample`,
`split`, `text` (Python fence), `assertions`, `n_assertions`, `llm_calls`, `n_in`,
`n_out`, `seconds`, `calls`, `model`, `run_id`, `facts_version`, and method diagnostics.
Offline token counts are zero. Manifests record budgets, task/response/source hashes
and original-source provenance. Existing runs require `--resume` and an identical
manifest. `--workers` runs samples in separate processes.

Workers use `unshare -rn`, an explicit credential-free environment, resource limits,
per-operation timeouts and process-group termination on total timeout. This is a
network and execution boundary, not a filesystem security boundary. No generated
code runs in the parent. Missing mutmut or incompatible APIs produce a recorded
failure, with no alternative mutation generator.

Extraction is static: aliases, simple local assignments, literal loops,
parameterization and unittest assertions are normalized. Unresolved fixtures or
names and unsupported assertions are recorded in `extraction_rejected`. Exception
checks can improve CoverUp coverage without producing equality assertions. Expected
values remain the baseline’s own (o0); common ref/full scoring must replace them for
the registered comparison. This implementation does not run or modify the scorer,
perform a held-out run, or estimate real-model effectiveness.

CPU verification from the repository root, using the existing environment:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 CoverUp_concept/.venv/bin/python -B -m pytest -q -p no:cacheprovider --basetemp=trickcatcher_linefacts/baselines/tests/.pytest_tmp trickcatcher_linefacts/baselines/tests
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 CoverUp_concept/.venv/bin/python -B -m trickcatcher_linefacts.baselines.tests.dry_run
```

The dry-run destination must be fresh; use `--out` with another directory under
`baselines/tests/` to repeat it. `tests/dev_tasks.json` contains only visible inputs
for HumanEval development tasks 2, 3, 4; `tests/dev_responses.json` is the fixed fake
script. Some expected values intentionally match buggy PUTs to exercise native
refinement/acceptance, not correctness against a reference.

Verification on 2026-10-13: **22 pytest tests passed**. Both baselines completed
three tasks × K=3, producing nine rows each. Summary and complete artifacts are in
`tests/dry_runs/`; per-baseline tables are documented in their READMEs. Python
3.11.14 and exact dependency versions are recorded in the summary and requirements.

2026-10-14 (dev sanity amendment 3): `QwenClient` now retries transient transport failures (timeouts, connection
errors, 5xx; up to 8 retries with backoff, 600 s timeout) with the identical payload and seed; 4xx is not retried.
2026-10-14 (amendment 4): an HTTP 400 "maximum context length" counts as a request made with an empty answer
(`ContextTooLong`, recorded as `error: context_length` in the call record) instead of aborting the run.

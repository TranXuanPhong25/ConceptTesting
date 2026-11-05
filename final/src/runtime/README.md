# Benchmark runtime

Shared infrastructure used by `final/src/modular`, independent of historical experiment
packages:

- `execution.py` creates a fresh `bwrap` sandbox and runs `worker.py`.
- `worker.py` loads a function, validates inputs, executes reference/PUT calls and
  serializes results. `contracts.py` supplies the sandbox validation helpers.
- `model.py` uses LangChain/OpenAI SDK for completion serialization and SSE decoding,
  with sanitized transport errors, explicit stream limits and completion guards.
  It retains vLLM `/models` and `/tokenize` requests and context budgeting.
- `checkpoint.py` records exact requests/responses and preserves retry history.
- `keepalive.py` records notebook keepalive calls separately.
- `artifacts.py` provides content hashes and atomic JSON writes.

An offline [LangChain probe](../audits/probe_langchain_transport.py) compares the
runtime adapter with plain ChatOpenAI. See the
[migration results](../../review/langchain_adapter_2026-11-05.md). The adapter
disables SDK retries/tracing, preserves partial output and raw provider usage,
and requires finish plus nonempty text. One private decoded-chunk hook preserves
choice-zero/usage policy; regression tests cover this integration. The SDK may
add null optional usage fields. Dependency versions are recorded in new manifests.

Install the tested transport versions into the pipeline environment:

```bash
uv pip install --python final/.venv/bin/python -r final/src/runtime/requirements.txt
```

The sandbox implementation is extracted unchanged from the earlier executor.
Retired experiment source is available through Git history; documentation and
results stay archived. The active runtime does not import those packages. Executor/module identity changes invalidate incompatible shared
cache entries. Existing run artifacts are never rewritten during this refactor.

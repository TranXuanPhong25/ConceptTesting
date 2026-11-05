# Benchmark runtime

Shared infrastructure used by `final/src/modular`, independent of historical experiment
packages:

- `execution.py` creates a fresh `bwrap` sandbox and runs `worker.py`.
- `worker.py` loads a function, validates inputs, executes reference/PUT calls and
  serializes results. `contracts.py` supplies the sandbox validation helpers.
- `model.py` provides streaming Qwen requests with sanitized transport errors.
- `checkpoint.py` records exact requests/responses and preserves retry history.
- `keepalive.py` records notebook keepalive calls separately.
- `artifacts.py` provides content hashes and atomic JSON writes.

The sandbox implementation is extracted unchanged from the earlier executor.
Retired experiment source is available through Git history; documentation and
results stay archived. The active runtime does not import those packages. Executor/module identity changes invalidate incompatible shared
cache entries. Existing run artifacts are never rewritten during this refactor.

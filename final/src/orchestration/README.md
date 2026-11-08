# Local run console (Prefect)

This uses Prefect's existing web UI, parameter forms, deployments, scheduler,
SQLite history, logs and artifacts. The adapter launches the existing benchmark
with the dedicated `final/.venv` Python; Prefect lives in `.venv_orchestration`.
Starting the server or registering/importing presets makes **zero LLM calls**.

```bash
./final/run_console.sh start
./final/run_console.sh status
./final/run_console.sh reload-presets
./final/run_console.sh clean-stale-history
./final/run_console.sh stop
```

Open <http://127.0.0.1:4200/deployments>. Select a deployment, choose **Run**, edit
parameters and launch now or schedule a custom run. The server and preset listener
must remain running. With no arguments the script defaults to `start`; missing
orchestration dependencies are installed into their separate venv.

## Presets

Presets are stored in `final/presets/run_console.json`. Registration resolves all
defaults into deployment parameters, so queued runs retain their exact values.

| Preset | Allocation | Maximum calls |
|---|---|---:|
| `full-batch-direct-soft` | 20 inputs/task/arm, one call/task/arm | 314 |
| `known10-batch-direct-soft` | 20 inputs/selected PUT/arm | 20 |
| `smoke3-batch-direct-soft` | Tasks 2/11/72, same full cohort | 6 |
| `full-soft-per-put-shared20` | 20 inputs/task shared across PUTs, usually 2–3/call | 1,454 |
| `resume-saved-run` | Continue a stopped Console/matched-batch directory | Missing slots only |

The known10 preset uses the *new common batch prompt*, not an exact replay of the
historical three-style prompt diagnostic. The per-PUT preset does **not** allocate
20 inputs to every PUT.

`preview_only=True` creates budget/config artifacts without a model, tokenizer or
native call. Use it to inspect budgets. `preview_only=False` starts real work when
you press Run. No agent launches a new model experiment merely by creating a preset.

## Settings and reproducibility

Forms expose cohort, task subset, mode, arms, inputs/task, output/context tokens,
temperature, generation/reference seeds, native timeout, per-PUT base examples,
served model name and scorer. Batch allows Direct/Soft BVA; per-PUT allows Boundary.
The cohort determines the expected PUT count (1 or10); it is not silently changed.
The output token limit is **per call**, and input budget is **per task per arm**.
`per_put_base_examples` only applies to per-PUT mode; batch sees original base tests.

Every real run gets a new directory under `final/out/console_<flow-id>/run`:

- Immutable resolved `config_snapshot.json`, offline budget preview and cohort hash
- A read-only snapshot of executing code/data, isolated from future worktree edits
- Registered requests/responses, retry/unknown history, input freeze and native checkpoints
- `status.json`, `progress.json`, `worker.log`, summary and result digest
- Source checks and immutable replay before a successful final status

The runtime's current conditional confirmation scorer and the historical
full-two-repeat scorer are separate explicit options. Both arms of a paired run
always share the chosen scorer. Native jobs use the existing shared execution lock.
The preset listener permits one run at a time and waits for existing external
model writers; this does not take ownership of the already running external batch.

Changing a preset never changes an already submitted run's parameters or snapshots.
After editing the preset JSON or runner code, run `./final/run_console.sh reload-presets`.
It refreshes UI forms/defaults without restarting Prefect's history server; it refuses
while a console-owned flow is queued/running.

## Stop/resume

Use Prefect's **Cancel** for a Console-owned run. Saved responses/checkpoints and
attempt caps remain. Then launch **resume-saved-run** with the source artifact
directory (`.../console_<id>/run`, not its parent submission directory).
Do **not** use generic Prefect Retry on the same flow ID: snapshot directories are
intentionally immutable. Resume creates a new output and preserves the old one.

Original matched-batch outputs are also supported. A live worker lock blocks
resume. Stale running status after process death can be recovered only with a
free worker lock and a worker-start marker, recorded explicitly in import receipts.
Per-request transport attempts are never reset; received responses are never
regenerated. Path-only reference/identity metadata is rebuilt in the new runtime.

## Historical runs

Existing BVA/prompt-style/naive/rescore outputs are indexed read-only into Prefect,
tagged `historical` and `read-only-index`. Config/result/progress/report artifacts
come from their saved files; indexing does not replay or execute the experiments.
They are not owned by Prefect, so use the existing process/checkpoint mechanisms
to control them. Their original directories stay unchanged.

If the historical table needs pruning, `clean-stale-history` makes a timestamped
metadata backup and removes only imported Prefect rows in Failed/Pending whose
source directories are stopped (`interrupted`/`prepared`). It leaves every source
artifact/checkpoint on disk and records a suppression entry so the watcher does
not reimport those rows. It does not clear managed Console runs or an active worker.

UI/server state: `final/out/run_console/prefect_home` (SQLite), logs and process
receipts in `final/out/run_console/`. Persistence is local, with no cloud account.
The service binds only to `127.0.0.1`.

## Endpoint/credentials

The local profile remains outside the repo:
`~/.config/concepttester/final-qwen.env`. Each run copies its routing/credentials
to a unique private file under `~/.config/concepttester/run-endpoints/` (0600).
URLs/API keys never enter Prefect parameters or config snapshots. Resume reads the
current local profile into a new private routing snapshot; benchmark settings stay
unchanged. Update the local profile before resuming if the notebook endpoint moved.

## Validation

```bash
final/.venv/bin/python -m pytest -q final/tests/test_orchestration.py
```

The UI smoke test uses preview-only mode; it makes no model or native calls.

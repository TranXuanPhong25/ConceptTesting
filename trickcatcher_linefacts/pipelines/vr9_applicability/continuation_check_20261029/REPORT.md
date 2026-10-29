# VR9 continuation readiness — 2026-10-29

Frozen implementation is intact and the pinned runtime is available locally.
The current shell and `/tmp` do not contain a recoverable authorized endpoint,
so this check made **zero metadata probes and zero completion calls**.

## Verified state

- All 80 `FREEZE.json` file hashes and all 63 parent hashes match.
- The readiness archive SHA256 and all 493 member hashes match its manifest.
- The archived diagnostic is blocked with `RuntimeError`; its archive contains
  no completion-attempt ledger and no transport completion receipts. This agrees
  with the documented earlier preflight HTTP404 / zero new completions.
- Local `out/humaneval/diagnostic/` is absent; the archived state is evidence of
  the historical attempt, not a live controller. No currently running process
  has the exact VR9 diagnostic module in its argument vector.
- `/tmp/pytoy-v84-venv` is absent. The existing interpreter
  `trickcatcher_linefacts/handoffs/v85_20261029/.venv/bin/python` has exactly
  Hypothesis 6.169.0, mutmut 3.8.0, coverage 7.16.2 and LibCST 1.9.0.
- Running the frozen `diagnostic check` with this interpreter passed integrity,
  ledger and tool-version checks without model calls. The diagnostic selects
  `sys.executable` as its worker runtime, so no frozen config edit is needed.
- No relevant endpoint variable existed before or after silently sourcing
  `scripts/research_env.sh`. A filename-only recursive `/tmp` scan found no
  authorized private endpoint environment file. No secret file was printed,
  and `scripts/openrouter_env.sh` was not inspected.

## Existing call guards

The frozen controller takes an exclusive nonblocking `RUN.lock`, verifies
hashes and rejects any failed/unresolved ledger entry before starting. It sets
the shared transport completion cap to 12; reservations are locked and unique,
and attempted keys cannot be retried. Strategy requests and strict/generic
requests must match inherited receipt keys exactly or abort. Only repaired-arm
expected-output requests can be fresh. There are two workers, no automatic
fallback/retry and a 900-second completion timeout.

The registered model is `qwen3.5-27b-awq`, context 8192. The next owner action
requires that exact advertised model/context at an authorized endpoint.
The historical request/body/receipt pools remain reusable inside frozen assets;
the archived native strict/generic results can additionally be restored from
the verified evidence archive if the owner chooses to resume those local files.

## Concrete continuation command

After the owner supplies/restores an authorized endpoint in the process
environment as `CT_RETRIEVAL_BASE_URL`, use the existing pinned runtime:

```sh
source scripts/research_env.sh >/dev/null 2>&1
export PYTHONDONTWRITEBYTECODE=1
trickcatcher_linefacts/handoffs/v85_20261029/.venv/bin/python \
  -m trickcatcher_linefacts.pipelines.vr9_applicability.diagnostic check
```

The parent agent should coordinate the single metadata probe and detached
`diagnostic run` only after checking current locks/ledger again. No controller
was launched during this check. The frozen source, readiness artifacts and
historical outputs were not changed. There is no new efficacy outcome.

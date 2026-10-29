# vr8: measured semantic gates

Retrieval experiment namespace: `vr8`, then `vr9`; LineFacts `vNN` names remain
unchanged. Parent: `v85_retrievalhybrid`. See `PREREG.md` for the frozen protocol.

This diagnostic replaces a selected card's line-reachability gate with a bound
observable predicate: normalization changes a string, membership differs from an
explicit vowel-class hypothesis, or string order differs from an alternative order.
An observation is not proof of a specification violation. Requirements can remain
unknown; propagation to the returned value is not verified. This follows the
ConceptCoder distinction between concepts and their measurements, without claiming
to reproduce its learned concept bottleneck or training.

Six development tasks, three arms (`old`, `semantic`, `generic`), identical saved
round1 and ten saved spec-only reference programs per task. Each arm gets two new
strategy slots and at most one expected-output call. This is a fixed-budget gate
diagnostic, not an unchanged V85 run. Canonical implementations and contracts are
decoded only by final scoring after generation is frozen. No automatic full113 run.

## Run

Use Python with the versions pinned in `v4_runtime.py` (current Mac interpreter:
`/tmp/pytoy-v84-venv/bin/python`). Source `scripts/research_env.sh` silently, then a
private environment file defining `CT_RETRIEVAL_BASE_URL`. Never save the endpoint
in this folder. External `LINEFACTS_*` overrides are rejected.

```sh
python -m trickcatcher_linefacts.pipelines.vr8_semanticgate.diagnostic check
python -m trickcatcher_linefacts.pipelines.vr8_semanticgate.diagnostic run
```

Run long generation detached and inspect `out/humaneval/diagnostic/STATUS.json`.
`RUN.lock` prevents concurrent controllers. Source and assets in `FREEZE.json`
must stay unchanged. A failed or unresolved completion blocks automatic resume;
an empty-ledger preflight failure can be retried when the endpoint is restored.
There is no fallback model. The physical completion cap is 54.

`assets/selection.json` records candidates and deterministic selection;
`assets/INHERITED.json` records reused source receipts. `CPU_CHECKS.json` records
local validation. `RESULTS.json` is produced only after all generation/scoring
completes: primary `ref`, secondary `o0`, paired task contrasts, novel semantic
inputs, unknown observations, logical/physical calls, and known token usage.
Inherited round1/reference costs are separate; these omit shared preparation costs.
Missing usage is reported as unknown, never assumed zero cost.

Interpretation is limited to these development tasks and supported AST bindings.
A mechanism claim needs semantic realizations beyond both controls; bug detection
alone does not show that a concept gate helped. See the candidate concepts and
paper-definition audit linked from `memory/v85-concept-quality.md`.

## Readiness — 2026-10-29

41 CPU tests pass, including native strategy/classification/final scoring with ten
saved reference programs. Selection frozen: 137,148 (ordering),51,98 (membership),
101,54 (normalization). CPU replay of saved round1: old gate covered6/6 tasks;
semantic predicate observed5/6, with task51 the sole uncovered target. Selection
was not changed after this observation. This is a coverage diagnostic, not a bug
score or evidence that vr8 improves generated tests.

The first controller stopped at endpoint preflight; `/models` returned HTTP404.
No new completion attempts, no generated vr8 tests, no efficacy result. The
empty completion ledger permits an explicit retry with the same frozen sources
once the endpoint is restored. No controller remains active.

## Completed — supersedes the preflight stop

The restored endpoint ran all6tasks/3arms. Primaryref:6/6confirmed,0false alarms
in every arm; savedR1already6/6. No added semantic realizations over controls.
Only task51 changed targeting: its correct vowel table made the requested fault
predicate impossible, and the hard filter discarded200valid candidate occurrences,
including a post-hoc confirmed bug-exposing input.20new completions/18,108tokens,
0failures/unknowns. No active controller or automatic expansion.
[Full result, limits, and evidence](completed/REPORT.md).
